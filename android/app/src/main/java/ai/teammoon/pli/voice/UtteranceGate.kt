package ai.teammoon.pli.voice

/** One SDK stream at a time. A result alone does not authorize the next stream. */
class UtteranceGate{
    @Volatile var state="READY";private set
    @Volatile var id=0L;private set
    private var completedInput=false;private var ended=false;private var quiet=0
    @Synchronized fun begin():Boolean{if(state!="READY")return false;id++;completedInput=false;ended=false;quiet=0;state="STREAMING";return true}
    @Synchronized fun complete():Boolean{if(state=="READY"||ended||completedInput)return false;completedInput=true;if(state=="STREAMING")state="WAITING";return true}
    @Synchronized fun result(){if(state in setOf("STREAMING","WAITING")){state="DRAINING";quiet=0}}
    @Synchronized fun end(){if(state!="READY"){ended=true;state="DRAINING";quiet=0}}
    @Synchronized fun silence(value:Boolean):Boolean{if(state!="DRAINING")return false;quiet=if(value)quiet+1 else 0;if(ended&&quiet>=3){state="READY";return true};return false}
    fun maySend(token:Long)=token==id&&state in setOf("STREAMING","WAITING")
    fun mayComplete(token:Long)=token==id&&!ended&&completedInput&&state in setOf("WAITING","DRAINING")
}
