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
//!   in [`WakePhase::AwakeInPod`]. The first poll there advances the machine
//!   to [`WakePhase::ExitingPod`].
//! * In [`WakePhase::Waking`] exit-pod intent is dropped, never buffered:
//!   the wake sequence must finish before the body responds, and an intent
//!   held from before the wake boundary must not queue an automatic exit.
//!   This is the documented early-input policy.
//! * In [`WakePhase::ExitingPod`] all input is ignored: the authored get-up
//!   motion owns the body until it signals completion.
//! * In [`WakePhase::Standing`] exit-pod intent is unbound and dropped.
//! * Together these rules make held and repeated exit intent transition the
//!   machine exactly once: only the first poll after the wake boundary finds
//!   [`WakePhase::AwakeInPod`], and every later poll lands in a phase whose
//!   policy drops the intent. No transition can be duplicated and none can
//!   skip.
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
    /// Awake, lying in the pod. Look is allowed and exit-pod intent is
    /// consumed.
    AwakeInPod,
    /// The authored get-up motion owns the body. All input is ignored.
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
    /// intent).
    ///
    /// Phase policy: in [`WakePhase::AwakeInPod`] the first poll advances to
    /// [`WakePhase::ExitingPod`]; in [`WakePhase::Waking`],
    /// [`WakePhase::ExitingPod`], and [`WakePhase::Standing`] the intent is
    /// dropped and [`PhaseTransition::Ignored`] is returned. The method is
    /// infallible by design: player input can never place the machine in an
    /// illegal state, and the only drop-or-consume decision is the phase.
    #[must_use]
    pub fn request_pod_exit(&mut self) -> PhaseTransition {
        if *self == Self::AwakeInPod {
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
    use super::{PhaseError, PhaseTransition, WakePhase};

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

    /// The legal transition out of `AwakeInPod` is the exit-pod input.
    #[test]
    fn exit_intent_advances_awake_in_pod_to_exiting_pod() {
        let mut phase = WakePhase::AwakeInPod;
        assert_eq!(
            phase.request_pod_exit(),
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
            phase.request_pod_exit(),
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
    /// phase holds through any number of polls.
    #[test]
    fn early_exit_intent_during_waking_is_ignored() {
        let mut phase = WakePhase::Waking;
        for _ in 0..5 {
            assert_eq!(phase.request_pod_exit(), PhaseTransition::Ignored);
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
    /// transition: the authored get-up owns the body.
    #[test]
    fn exit_intent_during_exiting_pod_cannot_re_trigger() {
        let mut phase = WakePhase::ExitingPod;
        for _ in 0..5 {
            assert_eq!(phase.request_pod_exit(), PhaseTransition::Ignored);
            assert!(phase.in_phase(WakePhase::ExitingPod));
        }
    }

    /// Exit intent at Standing is unbound and dropped; the phase holds.
    #[test]
    fn exit_intent_during_standing_is_ignored() {
        let mut phase = WakePhase::Standing;
        for _ in 0..3 {
            assert_eq!(phase.request_pod_exit(), PhaseTransition::Ignored);
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

    /// An exit intent held across the wake boundary transitions exactly
    /// once: dropped while Waking, consumed by the first poll after the
    /// boundary, dropped by every later poll.
    #[test]
    fn held_exit_intent_across_the_wake_boundary_transitions_exactly_once() {
        let mut phase = WakePhase::Waking;
        for _ in 0..3 {
            assert_eq!(phase.request_pod_exit(), PhaseTransition::Ignored);
        }
        assert_eq!(
            phase.wake_complete(),
            PhaseTransition::Advanced {
                from: WakePhase::Waking,
                to: WakePhase::AwakeInPod,
            }
        );
        assert_eq!(
            phase.request_pod_exit(),
            PhaseTransition::Advanced {
                from: WakePhase::AwakeInPod,
                to: WakePhase::ExitingPod,
            }
        );
        for _ in 0..3 {
            assert_eq!(phase.request_pod_exit(), PhaseTransition::Ignored);
        }
        assert!(phase.in_phase(WakePhase::ExitingPod));
        // The held intent never skips the get-up either.
        assert!(!phase.locomotion_allowed());
    }

    /// Repeated exit intent from `AwakeInPod` cannot skip the get-up: the
    /// machine stops at `ExitingPod` until the authored motion completes.
    #[test]
    fn repeated_exit_intent_cannot_skip_the_get_up() {
        let mut phase = WakePhase::AwakeInPod;
        assert_eq!(
            phase.request_pod_exit(),
            PhaseTransition::Advanced {
                from: WakePhase::AwakeInPod,
                to: WakePhase::ExitingPod,
            }
        );
        for _ in 0..10 {
            assert_eq!(phase.request_pod_exit(), PhaseTransition::Ignored);
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
        assert_eq!(phase.request_pod_exit(), PhaseTransition::Ignored);
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
