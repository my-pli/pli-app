package ai.teammoon.pli

import ai.teammoon.pli.domain.RenderBudget
import ai.teammoon.pli.domain.VehicleState
import ai.teammoon.pli.domain.VoicePhase
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Pli's repaint budget while it shares the head unit with the Pleos driving view (2026-11-15 measurement). */
class RenderBudgetTest {
    @Test fun `parked car is not driving`() {
        assertFalse(RenderBudget.driving(VehicleState(gear = "P", speedKmh = 0f)))
        assertFalse(RenderBudget.driving(VehicleState()))
    }

    @Test fun `drive gear, speed or a UX restriction mean driving`() {
        assertTrue(RenderBudget.driving(VehicleState(gear = "D", speedKmh = 0f)))
        assertTrue(RenderBudget.driving(VehicleState(gear = "N", speedKmh = 12f)))
        assertTrue(RenderBudget.driving(VehicleState(gear = "P", uxRestricted = true)))
    }

    @Test fun `the night scene is never posted at 60 a second`() {
        assertEquals(30, RenderBudget.stageFps(still = false))
        assertEquals(12, RenderBudget.stageFps(still = true))
    }

    @Test fun `screens hold still while the car drives or the system asks for less motion`() {
        assertTrue(RenderBudget.calm(reduceMotion = false, vehicle = VehicleState(gear = "D", speedKmh = 30f)))
        assertTrue(RenderBudget.calm(reduceMotion = true, vehicle = VehicleState(gear = "P", speedKmh = 0f)))
        assertFalse(RenderBudget.calm(reduceMotion = false, vehicle = VehicleState(gear = "P", speedKmh = 0f)))
    }

    @Test fun `voice bars move only while Pli listens or speaks`() {
        assertEquals(30, RenderBudget.waveFps(VoicePhase.LISTENING))
        assertEquals(30, RenderBudget.waveFps(VoicePhase.SPEAKING))
        assertEquals(2, RenderBudget.waveFps(VoicePhase.QUIET))
        assertEquals(2, RenderBudget.waveFps(VoicePhase.STOPPED))
    }
}
