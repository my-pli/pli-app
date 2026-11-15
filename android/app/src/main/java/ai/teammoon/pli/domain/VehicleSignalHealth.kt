package ai.teammoon.pli.domain

/** A service heartbeat does not prove that a vehicle-property read completed. */
object VehicleSignalHealth {
    fun stale(startedAt:Long,completedAt:Long,now:Long):Boolean {
        val baseline=if(completedAt>0)completedAt else startedAt
        return now<baseline || now-baseline>(if(completedAt>0)10_000L else 15_000L)
    }
}
