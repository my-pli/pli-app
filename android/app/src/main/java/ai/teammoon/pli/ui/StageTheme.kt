package ai.teammoon.pli.ui

import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import ai.teammoon.pli.R
import ai.teammoon.pli.domain.ConversationState
import ai.teammoon.pli.domain.VoicePhase

/**
 * "Night drive under the aurora": one palette for every Pli screen.
 * The animated sky, road and Pli are painted on the GPU behind the window ([StageBackdrop]);
 * everything Compose draws sits on it as glass, so the software-rendered window never paints
 * large gradients itself.
 */
internal object Stage {
    val SkyTop = Color(0xFF050819)
    val SkyMid = Color(0xFF0C1433)
    val Horizon = Color(0xFF241F55)
    val Ember = Color(0xFFFFB46B)
    val Mint = Color(0xFF6EF0C8)
    val Aurora = Color(0xFF3EE6C1)
    val Violet = Color(0xFFA493FF)
    val Rose = Color(0xFFFF8FC7)
    val Sky = Color(0xFF8FB8FF)
    val Gold = Color(0xFFFFD36B)
    val Coral = Color(0xFFFF8A7A)
    val Cream = Color(0xFFF7F2E8)
    val Soft = Color(0xFFC9CBE8)
    val Dim = Color(0xFF8E93C2)
    val Ink = Color(0xFF0B1028)
    val GlassFill = Color(0x1AFFFFFF)
    val GlassStrong = Color(0x2BFFFFFF)
    val GlassEdge = Color(0x40FFFFFF)
    val Font = FontFamily(Font(R.font.pretendard))
}

/** The colour of what Pli is doing right now: listening, thinking, speaking or resting. */
internal fun moodColor(state: ConversationState): Color = when {
    state.error != null -> Stage.Coral
    state.agentBusy -> Stage.Violet
    state.quiet || state.phase == VoicePhase.QUIET -> Stage.Sky
    state.phase == VoicePhase.SPEAKING -> Stage.Gold
    state.phase == VoicePhase.LISTENING -> Stage.Mint
    else -> Stage.Dim
}

/** Frosted-glass panel: a translucent fill with a light top edge, no blur (the window renders in software). */
internal fun Modifier.glass(radius: Dp = 26.dp, fill: Color = Stage.GlassFill, edge: Color = Stage.GlassEdge): Modifier {
    val shape = RoundedCornerShape(radius)
    return clip(shape)
        .background(Brush.verticalGradient(listOf(fill.copy(alpha = fill.alpha * 1.5f), fill)), shape)
        .border(1.dp, Brush.verticalGradient(listOf(edge, edge.copy(alpha = edge.alpha * .25f))), shape)
}

@Composable internal fun reduceMotion(): Boolean {
    val context = LocalContext.current
    return remember { Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f }
}
