class_name Controller
extends RefCounted
## Frozen first-person controller specification, ported from gone_sim
## controller.rs. Constants only: nothing here computes, everything here
## specifies. Units: meters, seconds, meters per second, up is positive Y.

## Radius of the player capsule, in meters (an adult shoulder half-width).
const CAPSULE_RADIUS: float = 0.30

## Total capsule height while standing, in meters.
const CAPSULE_STANDING_HEIGHT: float = 1.75

## Maximum ledge height the controller climbs with a step, in meters.
const STEP_UP_HEIGHT: float = 0.25

## Upper bound on sweep-and-slide iterations per fixed tick.
const SWEEP_ITERATION_BOUND: int = 8

## Allowed residual penetration after resolution, in meters.
const PENETRATION_TOLERANCE: float = 0.005

## Free-space margin required around the capsule at pod exit, in meters.
const POD_EXIT_CLEARANCE: float = 0.15

## Steady survival walking speed, in meters per second.
const SURVIVAL_WALK_SPEED: float = 0.9

## Walk speed multiplier applied at the first unsteady step after standing.
const STEADY_INITIAL_SPEED_FACTOR: float = 0.35

## Exponential steadying time constant, in seconds.
const STEADYING_TIME_CONSTANT: float = 1.2

## Input magnitude at which the move vector is normalized.
const MAX_INPUT_LENGTH: float = 1.0
