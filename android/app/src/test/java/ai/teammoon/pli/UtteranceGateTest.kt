package ai.teammoon.pli
import ai.teammoon.pli.voice.UtteranceGate
import org.junit.Assert.*
import org.junit.Test
class UtteranceGateTest{
 @Test fun finalDoesNotAdmitNewAudioUntilSdkEndAndSilence(){val g=UtteranceGate();assertTrue(g.begin());val old=g.id;g.result();repeat(5){g.silence(true)};assertEquals("DRAINING",g.state);assertFalse(g.begin());assertFalse(g.maySend(old));assertFalse(g.mayComplete(old));assertTrue(g.complete());assertTrue(g.mayComplete(old));assertFalse(g.complete());g.end();repeat(3){g.silence(true)};assertEquals("READY",g.state);assertTrue(g.begin());assertFalse(g.maySend(old));assertTrue(g.maySend(g.id))}
 @Test fun emptyEndAndDuplicateTerminalCallbacksAreSafe(){val g=UtteranceGate();assertTrue(g.begin());assertTrue(g.complete());g.end();repeat(3){g.silence(true)};g.end();g.result();assertEquals("READY",g.state);assertTrue(g.begin());g.complete();assertTrue(g.mayComplete(g.id));g.result();assertTrue(g.mayComplete(g.id));g.end();assertFalse(g.mayComplete(g.id))}
}
