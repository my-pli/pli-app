package ai.teammoon.pli.domain

/**
 * The live microphone level (0..1), ten times a second while listening.
 *
 * Kept out of [ConversationState] on purpose: every state change recomposes and repaints the
 * whole software-rendered window, and the level alone made that happen ten times a second
 * (main thread ~85% busy while Pli simply listened, 2026-11-13). The vsync-paced surfaces read
 * it when they draw their next frame instead.
 */
object MicLevel {
    @Volatile var value: Float = 0f
}
