package ai.teammoon.pli.domain

/**
 * How often Pli may repaint while it shares the head unit with the vehicle's own display.
 *
 * Measured on the public Pleos emulator (2026-11-15): with Pli idle the Pleos driving view redraws
 * 28.6 times a second; while Pli answers it fell to 13-20, and to 8 while an answer card appeared.
 * Pli was posting its night scene 60 times a second and its voice bars 30 times a second (each post
 * makes the display compose the whole 2560x1440 screen again), and its software-rendered window
 * repainted for every typed word and every frame of a card's entry. While the car drives, Pli keeps
 * to a budget: the scene at a calm rate (still while restricted), the bars only while it listens or
 * speaks, and answers shown whole instead of typed in (also less to look at for the driver).
 */
object RenderBudget {
    const val STAGE_FPS = 30
    const val STAGE_STILL_FPS = 12
    const val WAVE_ACTIVE_FPS = 30
    const val WAVE_IDLE_FPS = 2

    /** The car is moving or restricted: no typing or entry motion in the window. */
    fun driving(vehicle: VehicleState): Boolean =
        vehicle.uxRestricted || vehicle.gear == "D" || (vehicle.speedKmh ?: 0f) > 1f

    /**
     * No entry, typing or title motion in the software-rendered window: the system asks for less motion, or the car drives.
     * (v10 re-take: the answer title's 0.5 s slide-in and the 0.26 s screen entry still ran while driving and took the
     * Pleos driving view to 8-11 redraws/s at every new answer.)
     */
    fun calm(reduceMotion: Boolean, vehicle: VehicleState): Boolean = reduceMotion || driving(vehicle)

    fun stageFps(still: Boolean): Int = if (still) STAGE_STILL_FPS else STAGE_FPS

    fun waveFps(phase: VoicePhase): Int =
        if (phase == VoicePhase.LISTENING || phase == VoicePhase.SPEAKING) WAVE_ACTIVE_FPS else WAVE_IDLE_FPS
}
