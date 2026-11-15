package ai.teammoon.pli.voice

/** AAOS may defer task teardown for 10s; reopening still needs a new window. */
internal object WindowRecoveryPolicy {
 const val GRACE_MS=15000L
 fun acknowledges(previous:String,current:String,visible:Boolean,until:Long,now:Long):Boolean =
  visible && current.isNotBlank() && current!=previous && now<until
}
