package ai.teammoon.pli
import ai.teammoon.pli.voice.WindowRecoveryPolicy as P
import org.junit.Assert.*
import org.junit.Test
class WindowRecoveryPolicyTest{
 @Test fun aStillVisibleRemovedWindowCannotAcknowledgeItsOwnReplacement(){
  assertFalse(P.acknowledges("old","old",true,15000,5000))
  assertFalse(P.acknowledges("old","",true,15000,5000))
  assertFalse(P.acknowledges("old","new",false,15000,5000))
  assertTrue(P.acknowledges("old","new",true,15000,12000))
  assertFalse(P.acknowledges("old","new",true,15000,15000))
  assertFalse(P.acknowledges("old","new",true,0,0))
 }
}
