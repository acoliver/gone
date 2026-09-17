//! The wake phase contract (issue #7 stage A).
//!
//! One progression governs the opening beat: [`WakePhase::Waking`] to
//! [`WakePhase::AwakeInPod`] to [`WakePhase::ExitingPod`] to
//! [`WakePhase::Standing`]. The machine lives in `gone_sim` so the wake pass
//! (issue #8) and the door beat (issue #11) consume one shared contract, and
//! so every policy below is testable without a renderer. No Bevy or render
//! type appears here; the app wraps [`WakePhase`] in its own resource.
//!
//! # Input policy (documented and frozen)
//!
//! * Exit-pod intent, the restraint pop / swing-out input, is consumed only
//!   in [`WakePhase::AwakeInPod`] and only on a fresh press edge
//!   ([`InputEdge::Rising`]). The first fresh press polled there advances
//!   the machine to [`WakePhase::ExitingPod`].
//! * A continued hold ([`InputEdge::Held`]) is dropped in every phase,
//!   including `AwakeInPod`: an exit input held from before the wake
//!   boundary is still a hold after the boundary, and the documented
//!   early-input policy is that it must not queue an automatic exit. The
//!   player presses again after waking to leave the pod.
//! * In [`WakePhase::Waking`] exit-pod intent is dropped, never buffered:
//!   the wake sequence must finish before the body responds, and both fresh
//!   presses and holds are dropped while it runs.
//! * In [`WakePhase::ExitingPod`] exit intent and locomotion are ignored
//!   (the authored get-up motion owns the body until it signals
//!   completion), but look stays allowed per the look policy below: user
//!   look composes with the authored get-up pose without resetting it.
//!   "All input is ignored" never appears in this contract; the ignored
//!   inputs are named exactly.
//! * In [`WakePhase::Standing`] exit-pod intent is unbound and dropped.
//! * Together these rules make held and repeated exit intent transition the
//!   machine exactly once: only a fresh press polled in
//!   [`WakePhase::AwakeInPod`] finds a consuming phase, every other poll
//!   lands on a hold edge or a phase whose policy drops the intent. No
//!   transition can be duplicated and none can skip.
//! * [`WakePhase::wake_complete`] and [`WakePhase::get_up_complete`] are
//!   idempotent boundary signals. Re-delivering a signal after its boundary
//!   is a no-op, so a signal held across a rendered frame cannot duplicate a
//!   transition.
//! * The only illegal call shape is [`WakePhase::get_up_complete`] signaled
//!   before [`WakePhase::ExitingPod`], which would skip phases. It fails
//!   loudly with [`PhaseError`] and leaves the phase unchanged.
//!
//! # Query policy (documented and frozen)
//!
//! * [`WakePhase::look_allowed`] is false only in [`WakePhase::Waking`]: the
//!   player may look from the first held blink onward, and user look composes
//!   with the authored get-up pose and sway without resetting either.
//! * [`WakePhase::locomotion_allowed`] is true only in [`WakePhase::Standing`]:
//!   `WASD` cannot translate the player before the get-up completes. This is
//!   the single locomotion predicate; nothing else unlocks translation.
//!
//! Every predicate and every transition match is exhaustive over the enum.
//! A closed enum with no wildcard arm is the fail-loud guarantee: there is
//! no unknown state and no fallback path to stack behavior onto.

/// Whether one poll of a possibly-held input is a fresh press or a
/// continuation of a hold.
///
/// Boundary-crossing actions are keyed to the fresh press: a hold carried
/// across a phase boundary stays a hold there and never fires the action
/// the boundary's phase would consume. Callers derive the edge from their
/// own previous button state; the machine never guesses.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum InputEdge {
    /// The input rose from released to pressed since the previous poll.
    Rising,
    /// The input was already held at the previous poll and stayed held.
    Held,
}

/// What one transition attempt did to the machine.
///
/// Every attempt returns exactly one outcome. There is no implicit state and
/// no silent fallback: callers can assert the full outcome in scenarios.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PhaseTransition {
    /// The phase advanced from `from` to `to`.
    Advanced {
        /// The phase before the attempt.
        from: WakePhase,
        /// The phase after the attempt.
        to: WakePhase,
    },
    /// A boundary signal was re-delivered after its boundary had already
    /// passed. The phase is unchanged; the signal fires exactly once.
    AlreadyDelivered,
    /// An input poll was dropped under the phase's documented input policy.
    /// The phase is unchanged.
    Ignored,
}

/// A rejected transition attempt.
///
/// The machine has exactly one illegal call shape: the get-up-complete
/// signal arriving before the get-up has started. Rejections never mutate
/// the phase.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PhaseError {
    /// [`WakePhase::get_up_complete`] was signaled while the machine sat in
    /// `current`, where the get-up has not started. The skip is rejected and
    /// the phase is unchanged.
    GetUpBeforeExitingPod {
        /// The phase the machine was in when the signal arrived.
        current: WakePhase,
    },
}

impl std::fmt::Display for PhaseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::GetUpBeforeExitingPod { current } => write!(
                f,
                "get-up-complete signaled in phase {current:?}: the get-up has not \
                 started, the skip is rejected, and the phase is unchanged"
            ),
        }
    }
}

impl std::error::Error for PhaseError {}

/// The player's phase through the opening wake beat.
///
/// Spawn state is [`WakePhase::Waking`]. The machine only ever advances
/// forward, exactly one phase per transition; no function moves it backward.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub enum WakePhase {
    /// Eyes not yet open in the seventh pod. Nothing is controllable.
    #[default]
    Waking,
    /// Awake, lying in the pod. Look is allowed and a fresh exit-pod press
    /// is consumed.
    AwakeInPod,
    /// The authored get-up motion owns the body: exit intent and locomotion
    /// are ignored. Look stays allowed and composes with the authored pose.
    ExitingPod,
    /// On foot. `WASD` locomotion is unlocked.
    Standing,
}

impl WakePhase {
    /// Consume one poll of the wake-complete boundary signal.
    ///
    /// In [`WakePhase::Waking`] this advances to [`WakePhase::AwakeInPod`].
    /// Re-delivery in any later phase returns
    /// [`PhaseTransition::AlreadyDelivered`] and changes nothing, so the
    /// wake pass (issue #8) may hold or repeat the signal freely.
    #[must_use]
    pub fn wake_complete(&mut self) -> PhaseTransition {
        if *self == Self::Waking {
            return self.advance_to(Self::AwakeInPod);
        }
        PhaseTransition::AlreadyDelivered
    }

    /// Feed one poll of the exit-pod input (restraint pop / swing-out
    /// intent), tagged with the poll's [`InputEdge`].
    ///
    /// Phase and edge policy: a [`InputEdge::Rising`] poll in
    /// [`WakePhase::AwakeInPod`] advances to [`WakePhase::ExitingPod`]. A
    /// [`InputEdge::Held`] poll is dropped in every phase, so a hold carried
    /// across the wake boundary never queues an exit. A rising poll in any
    /// other phase is dropped too: [`PhaseTransition::Ignored`] with the
    /// phase unchanged. The method is infallible by design: player input can
    /// never place the machine in an illegal state, and the only
    /// drop-or-consume decisions are the phase and the edge.
    #[must_use]
    pub fn request_pod_exit(&mut self, edge: InputEdge) -> PhaseTransition {
        if *self == Self::AwakeInPod && edge == InputEdge::Rising {
            return self.advance_to(Self::ExitingPod);
        }
        PhaseTransition::Ignored
    }

    /// Consume one poll of the get-up-complete boundary signal.
    ///
    /// In [`WakePhase::ExitingPod`] this advances to [`WakePhase::Standing`].
    /// Re-delivery in [`WakePhase::Standing`] returns
    /// [`PhaseTransition::AlreadyDelivered`] and changes nothing.
    ///
    /// # Errors
    /// [`PhaseError::GetUpBeforeExitingPod`] when signaled in
    /// [`WakePhase::Waking`] or [`WakePhase::AwakeInPod`]: the get-up has not
    /// started, so the signal would skip phases. The phase is left unchanged.
    pub fn get_up_complete(&mut self) -> Result<PhaseTransition, PhaseError> {
        match *self {
            Self::ExitingPod => Ok(self.advance_to(Self::Standing)),
            Self::Standing => Ok(PhaseTransition::AlreadyDelivered),
            current => Err(PhaseError::GetUpBeforeExitingPod { current }),
        }
    }

    /// Advance one step to `next` and return the recorded transition.
    fn advance_to(&mut self, next: Self) -> PhaseTransition {
        let from = *self;
        *self = next;
        PhaseTransition::Advanced { from, to: next }
    }

    /// Whether the player may drive the camera this frame.
    ///
    /// The documented look policy: look is allowed from
    /// [`WakePhase::AwakeInPod`] onward and from nothing before it.
    #[must_use]
    pub fn look_allowed(self) -> bool {
        !matches!(self, Self::Waking)
    }

    /// Whether `WASD` may translate the player this frame.
    ///
    /// The single locomotion predicate: true only in [`WakePhase::Standing`].
    #[must_use]
    pub fn locomotion_allowed(self) -> bool {
        matches!(self, Self::Standing)
    }

    /// Whether the machine currently sits in `candidate`.
    #[must_use]
    pub fn in_phase(self, candidate: Self) -> bool {
        self == candidate
    }
}

/// Exhaustive, pure coverage of the phase contract: every legal transition,
/// every rejection, the input policy, the idempotence rules, and both query
/// predicates over all phases.
#[cfg(test)]
mod tests {
    use super::{InputEdge, PhaseError, PhaseTransition, WakePhase};

    /// All four phases in progression order.
    const ALL: [WakePhase; 4] = [
        WakePhase::Waking,
        WakePhase::AwakeInPod,
        WakePhase::ExitingPod,
        WakePhase::Standing,
    ];

    /// Spawn state is Waking, with both policies locked.
    #[test]
    fn spawn_phase_is_waking_with_look_and_locomotion_locked() {
        let phase = WakePhase::default();
        assert!(phase.in_phase(WakePhase::Waking));
        assert!(!phase.look_allowed());
        assert!(!phase.locomotion_allowed());
    }

    /// The legal transition out of Waking is wake-complete alone.
    #[test]
    fn wake_complete_advances_waking_to_awake_in_pod() {
        let mut phase = WakePhase::Waking;
        assert_eq!(
            phase.wake_complete(),
            PhaseTransition::Advanced {
                from: WakePhase::Waking,
                to: WakePhase::AwakeInPod,
            }
        );
        assert!(phase.in_phase(WakePhase::AwakeInPod));
    }

    /// The legal transition out of `AwakeInPod` is a fresh exit-pod press.
    #[test]
    fn exit_intent_advances_awake_in_pod_to_exiting_pod() {
        let mut phase = WakePhase::AwakeInPod;
        assert_eq!(
            phase.request_pod_exit(InputEdge::Rising),
            PhaseTransition::Advanced {
                from: WakePhase::AwakeInPod,
                to: WakePhase::ExitingPod,
            }
        );
        assert!(phase.in_phase(WakePhase::ExitingPod));
    }

    /// The legal transition out of `ExitingPod` is get-up-complete.
    #[test]
    fn get_up_complete_advances_exiting_pod_to_standing() {
        let mut phase = WakePhase::ExitingPod;
        assert_eq!(
            phase.get_up_complete(),
            Ok(PhaseTransition::Advanced {
                from: WakePhase::ExitingPod,
                to: WakePhase::Standing,
            })
        );
        assert!(phase.in_phase(WakePhase::Standing));
    }

    /// The whole progression walks forward one phase at a time to Standing.
    #[test]
    fn full_progression_reaches_standing_through_every_boundary() {
        let mut phase = WakePhase::Waking;
        assert!(!phase.look_allowed() && !phase.locomotion_allowed());
        assert_eq!(
            phase.wake_complete(),
            PhaseTransition::Advanced {
                from: WakePhase::Waking,
                to: WakePhase::AwakeInPod,
            }
        );
        assert!(phase.look_allowed() && !phase.locomotion_allowed());
        assert_eq!(
            phase.request_pod_exit(InputEdge::Rising),
            PhaseTransition::Advanced {
                from: WakePhase::AwakeInPod,
                to: WakePhase::ExitingPod,
            }
        );
        assert!(phase.look_allowed() && !phase.locomotion_allowed());
        assert_eq!(
            phase.get_up_complete(),
            Ok(PhaseTransition::Advanced {
                from: WakePhase::ExitingPod,
                to: WakePhase::Standing,
            })
        );
        assert!(phase.look_allowed() && phase.locomotion_allowed());
        assert!(phase.in_phase(WakePhase::Standing));
    }

    /// Early exit intent during Waking is dropped, never buffered, and the
    /// phase holds through any number of polls: the first poll of a fresh
    /// press and every poll of the hold that follows it.
    #[test]
    fn early_exit_intent_during_waking_is_ignored() {
        let mut phase = WakePhase::Waking;
        assert_eq!(
            phase.request_pod_exit(InputEdge::Rising),
            PhaseTransition::Ignored
        );
        for _ in 0..4 {
            assert_eq!(
                phase.request_pod_exit(InputEdge::Held),
                PhaseTransition::Ignored
            );
            assert!(phase.in_phase(WakePhase::Waking));
        }
        // The dropped intent must not queue: waking still stops at
        // AwakeInPod instead of exiting automatically.
        assert_eq!(
            phase.wake_complete(),
            PhaseTransition::Advanced {
                from: WakePhase::Waking,
                to: WakePhase::AwakeInPod,
            }
        );
        assert!(phase.in_phase(WakePhase::AwakeInPod));
    }

    /// Get-up-complete in Waking is a rejected skip; the phase is unchanged.
    #[test]
    fn get_up_complete_during_waking_is_rejected() {
        let mut phase = WakePhase::Waking;
        assert_eq!(
            phase.get_up_complete(),
            Err(PhaseError::GetUpBeforeExitingPod {
                current: WakePhase::Waking,
            })
        );
        assert!(phase.in_phase(WakePhase::Waking));
    }

    /// Get-up-complete in `AwakeInPod` is a rejected skip; the phase is
    /// unchanged.
    #[test]
    fn get_up_complete_during_awake_in_pod_is_rejected() {
        let mut phase = WakePhase::AwakeInPod;
        assert_eq!(
            phase.get_up_complete(),
            Err(PhaseError::GetUpBeforeExitingPod {
                current: WakePhase::AwakeInPod,
            })
        );
        assert!(phase.in_phase(WakePhase::AwakeInPod));
    }

    /// Repeated exit intent during `ExitingPod` cannot re-trigger the
    /// transition: the authored get-up owns the body, fresh presses and
    /// holds alike.
    #[test]
    fn exit_intent_during_exiting_pod_cannot_re_trigger() {
        let mut phase = WakePhase::ExitingPod;
        assert_eq!(
            phase.request_pod_exit(InputEdge::Rising),
            PhaseTransition::Ignored
        );
        for _ in 0..4 {
            assert_eq!(
                phase.request_pod_exit(InputEdge::Held),
                PhaseTransition::Ignored
            );
            assert!(phase.in_phase(WakePhase::ExitingPod));
        }
    }

    /// Exit intent at Standing is unbound and dropped; the phase holds.
    #[test]
    fn exit_intent_during_standing_is_ignored() {
        let mut phase = WakePhase::Standing;
        for _ in 0..3 {
            assert_eq!(
                phase.request_pod_exit(InputEdge::Rising),
                PhaseTransition::Ignored
            );
            assert!(phase.in_phase(WakePhase::Standing));
        }
    }

    /// Wake-complete re-delivery is a no-op in every later phase: the
    /// signal fires exactly once.
    #[test]
    fn wake_complete_re_delivery_is_idempotent_in_every_later_phase() {
        for &start in ALL.iter().skip(1) {
            let mut phase = start;
            assert_eq!(phase.wake_complete(), PhaseTransition::AlreadyDelivered);
            assert!(phase.in_phase(start));
        }
    }

    /// Get-up-complete re-delivery at Standing is a no-op: the signal fires
    /// exactly once.
    #[test]
    fn get_up_complete_re_delivery_is_idempotent_in_standing() {
        let mut phase = WakePhase::Standing;
        assert_eq!(
            phase.get_up_complete(),
            Ok(PhaseTransition::AlreadyDelivered)
        );
        assert!(phase.in_phase(WakePhase::Standing));
    }

    /// An exit input held from before the wake boundary must not cause an
    /// exit: its polls are drops while Waking, the post-boundary polls are
    /// still holds and are dropped too, and the machine waits in
    /// `AwakeInPod` for a fresh press. Regression guard for the press-edge
    /// policy: the level-signal API used to let the first post-boundary
    /// poll consume the pre-boundary hold.
    #[test]
    fn held_exit_intent_crossing_the_wake_boundary_does_not_exit() {
        let mut phase = WakePhase::Waking;
        // The input went down before the wake boundary: one rising poll,
        // then the hold continues while waking runs.
        assert_eq!(
            phase.request_pod_exit(InputEdge::Rising),
            PhaseTransition::Ignored
        );
        for _ in 0..3 {
            assert_eq!(
                phase.request_pod_exit(InputEdge::Held),
                PhaseTransition::Ignored
            );
        }
        assert_eq!(
            phase.wake_complete(),
            PhaseTransition::Advanced {
                from: WakePhase::Waking,
                to: WakePhase::AwakeInPod,
            }
        );
        // The same held input persists past the boundary and never fires.
        for _ in 0..5 {
            assert_eq!(
                phase.request_pod_exit(InputEdge::Held),
                PhaseTransition::Ignored
            );
            assert!(phase.in_phase(WakePhase::AwakeInPod));
        }
        // A fresh press after the boundary is the only thing that exits,
        // exactly once.
        assert_eq!(
            phase.request_pod_exit(InputEdge::Rising),
            PhaseTransition::Advanced {
                from: WakePhase::AwakeInPod,
                to: WakePhase::ExitingPod,
            }
        );
        for _ in 0..3 {
            assert_eq!(
                phase.request_pod_exit(InputEdge::Rising),
                PhaseTransition::Ignored
            );
            assert_eq!(
                phase.request_pod_exit(InputEdge::Held),
                PhaseTransition::Ignored
            );
        }
        assert!(phase.in_phase(WakePhase::ExitingPod));
        // The held intent never skips the get-up either.
        assert!(!phase.locomotion_allowed());
    }

    /// A hold polled for the first time in `AwakeInPod` (a press that began
    /// before the poller started tracking edges) is a hold, not a press,
    /// and is dropped.
    #[test]
    fn held_intent_polled_in_awake_in_pod_is_dropped() {
        let mut phase = WakePhase::AwakeInPod;
        assert_eq!(phase.wake_complete(), PhaseTransition::AlreadyDelivered);
        assert_eq!(
            phase.request_pod_exit(InputEdge::Held),
            PhaseTransition::Ignored
        );
        assert!(phase.in_phase(WakePhase::AwakeInPod));
    }

    /// Repeated exit intent from `AwakeInPod` cannot skip the get-up: the
    /// machine stops at `ExitingPod` until the authored motion completes.
    #[test]
    fn repeated_exit_intent_cannot_skip_the_get_up() {
        let mut phase = WakePhase::AwakeInPod;
        assert_eq!(
            phase.request_pod_exit(InputEdge::Rising),
            PhaseTransition::Advanced {
                from: WakePhase::AwakeInPod,
                to: WakePhase::ExitingPod,
            }
        );
        for _ in 0..10 {
            assert_eq!(
                phase.request_pod_exit(InputEdge::Rising),
                PhaseTransition::Ignored
            );
        }
        assert!(phase.in_phase(WakePhase::ExitingPod));
        phase
            .get_up_complete()
            .expect("get-up signal is legal here");
        assert!(phase.in_phase(WakePhase::Standing));
    }

    /// At Standing no input or signal moves the machine backward or further.
    #[test]
    fn standing_phase_never_regresses() {
        let mut phase = WakePhase::Standing;
        assert_eq!(phase.wake_complete(), PhaseTransition::AlreadyDelivered);
        assert_eq!(
            phase.request_pod_exit(InputEdge::Rising),
            PhaseTransition::Ignored
        );
        assert_eq!(
            phase.get_up_complete(),
            Ok(PhaseTransition::AlreadyDelivered)
        );
        assert!(phase.in_phase(WakePhase::Standing));
    }

    /// The look policy over all phases: allowed from `AwakeInPod`, nothing
    /// before it.
    #[test]
    fn look_policy_per_phase() {
        let expected = [
            (WakePhase::Waking, false),
            (WakePhase::AwakeInPod, true),
            (WakePhase::ExitingPod, true),
            (WakePhase::Standing, true),
        ];
        for &(phase, allowed) in &expected {
            assert_eq!(phase.look_allowed(), allowed, "look in {phase:?}");
        }
    }

    /// The locomotion policy over all phases: Standing only.
    #[test]
    fn locomotion_policy_per_phase() {
        for &phase in &ALL {
            assert_eq!(
                phase.locomotion_allowed(),
                phase == WakePhase::Standing,
                "locomotion in {phase:?}"
            );
        }
    }

    /// `in_phase` is the identity check over the full truth table.
    #[test]
    fn in_phase_matches_only_itself() {
        for &phase in &ALL {
            for &candidate in &ALL {
                assert_eq!(
                    phase.in_phase(candidate),
                    phase == candidate,
                    "{phase:?} against {candidate:?}"
                );
            }
        }
    }

    /// The rejection error names the offending phase and the machine stays
    /// put after it.
    #[test]
    fn rejection_names_the_phase_and_leaves_the_machine_put() {
        for &start in ALL.iter().take(2) {
            let mut phase = start;
            let err = phase
                .get_up_complete()
                .expect_err("get-up signal before ExitingPod must be rejected");
            assert_eq!(err, PhaseError::GetUpBeforeExitingPod { current: start });
            assert!(phase.in_phase(start));
            let text = err.to_string();
            assert!(text.contains("get-up-complete"), "display: {text}");
            assert!(text.contains(&format!("{start:?}")), "display: {text}");
        }
    }
}
