package ai.teammoon.pli

import ai.teammoon.pli.domain.VehicleSignalHealth
import org.junit.Assert.*
import org.junit.Test

class VehicleSignalHealthTest {
    @Test fun aLiveProcessWithoutCompletedReadsEventuallyLosesItsVehicleValues(){assertFalse(VehicleSignalHealth.stale(1000,0,16000));assertTrue(VehicleSignalHealth.stale(1000,0,16001));assertFalse(VehicleSignalHealth.stale(1000,17000,27000));assertTrue(VehicleSignalHealth.stale(1000,17000,27001))}
    @Test fun newReadRestoresFreshnessAndAClockResetCannotKeepAnOldValueAlive(){assertFalse(VehicleSignalHealth.stale(1000,28000,28001));assertTrue(VehicleSignalHealth.stale(1000,28000,1000))}
}
