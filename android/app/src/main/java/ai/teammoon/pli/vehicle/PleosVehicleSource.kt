package ai.teammoon.pli.vehicle

import android.car.Car
import android.car.VehiclePropertyIds
import android.car.VehicleGear
import android.car.hardware.CarPropertyValue
import android.car.hardware.property.CarPropertyManager
import android.car.drivingstate.CarUxRestrictionsManager
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import ai.pleos.playground.vehicle.Vehicle
import ai.pleos.playground.vehicle.api.model.area.DoorArea
import ai.pleos.playground.vehicle.api.model.area.WindowArea
import ai.pleos.playground.vehicle.constant.area.DoorValue
import ai.pleos.playground.vehicle.constant.area.WindowValue
import ai.pleos.playground.vehicle.constant.area.TurnSignalValue
import ai.pleos.playground.vehicle.constant.control.WiperState
import ai.pleos.playground.vehicle.listener.*
import ai.pleos.playground.navi.helper.NaviHelper
import ai.pleos.playground.navi.helper.listener.NaviHelperEventListener
import ai.pleos.playground.navi.data.*
import ai.pleos.playground.navi.constants.NaviErrorCode
import ai.teammoon.pli.domain.VehicleState
import ai.teammoon.pli.domain.VehicleSignalHealth
import ai.teammoon.pli.domain.DestinationChoice
import ai.pleos.playground.location.fused.FusedLocation
import ai.pleos.playground.location.fused.listener.FusedLocationListener
import ai.pleos.playground.location.fused.model.LocationData
import kotlin.math.ceil
import kotlinx.coroutines.*

/** Public typed Pleos APIs plus the AAOS-aligned speed, gear and UX restriction APIs. No vehicle writes. */
class PleosVehicleSource(
    private val context: Context,
    private val onState: (VehicleState) -> Unit,
    private val onEvent: (String) -> Unit,
    private val onIssue: (String) -> Unit
) {
    private val main=Handler(Looper.getMainLooper())
    private val reads=CoroutineScope(SupervisorJob()+Dispatchers.IO)
    private var state=VehicleState()
    private var vehicle:Vehicle?=null
    private var car:Car?=null
    private var propertyManager:CarPropertyManager?=null
    private var uxManager:CarUxRestrictionsManager?=null
    private var navi:NaviHelper?=null
    private var fused:FusedLocation?=null
    @Volatile private var naviReady=false
    @Volatile private var guiding=false
    @Volatile private var routeTarget:Pair<DestinationChoice,String>?=null
    @Volatile private var closed=false
    private val coreStartedAt=SystemClock.elapsedRealtime()
    @Volatile private var coreCompletedAt=0L
    private fun coreStale()=VehicleSignalHealth.stale(coreStartedAt,coreCompletedAt,SystemClock.elapsedRealtime())
    private val coreHealthTick=object:Runnable{override fun run(){if(closed)return;if(coreStale())update{it};main.postDelayed(this,1000)}}
    private val cleanup=mutableListOf<()->Unit>()
    private val doorPositions=mutableMapOf<DoorArea,Int>()
    private var wiperWasOn=false
    private var previousTurn="OFF"
    private var nearArrival=false
    private var chargeWasOn=false
    private fun update(change:(VehicleState)->VehicleState){main.post{if(!closed){state=change(state);if(coreStale())state=state.copy(gear="—",speedKmh=null,source="차량 속도·기어 신호를 확인하지 못했어요");onState(state)}}}
    private fun event(name:String){main.post{if(!closed)onEvent(name)}}
    private fun issue(domain:String,e:Throwable){Log.w("PliVehicle","$domain: ${e.message}");main.post{if(!closed)onIssue("$domain · ${e.message?.take(90) ?: e.javaClass.simpleName}")}}
    fun start(){
        main.post(coreHealthTick)
        try{
            val v=Vehicle(context.applicationContext);vehicle=v;v.initialize()
            update{it.copy(connected=true,source="Pleos Vehicle 2.3.2")}
            subscribeDoors(v);subscribeWiper(v);subscribeTurnSignal(v);subscribeBattery(v);subscribeDistance(v)
        }catch(e:Exception){issue("Vehicle SDK",e);update{it.copy(source="Vehicle 서비스 연결 대기")}}
        try{
            car=Car.createCar(context,main,Car.CAR_WAIT_TIMEOUT_DO_NOT_WAIT){connectedCar,ready->
                if(ready&&!closed){reads.launch{subscribeAaos(connectedCar)}}else if(!closed){update{it.copy(gear="—",speedKmh=null)}}
            }
        }catch(e:Exception){issue("AAOS",e)}
        try{
            val helper=NaviHelper(context.applicationContext);navi=helper
            helper.initialize(onConnected={if(!closed){naviReady=true;helper.addListener(naviListener);helper.getRouteStateInfo();helper.getDestinationInfo()}},onFailed={issue("NaviHelper",it)})
        }catch(e:Exception){issue("NaviHelper",e)}
        try{val f=FusedLocation(context.applicationContext);if(f.isSupported()){fused=f;f.initialize();f.registerFusedLocationCallback(locationListener)}}catch(e:Exception){issue("FusedLocation",e)}
    }
    private val locationListener=object:FusedLocationListener{
        override fun onChanged(location:LocationData?){if(location!=null&&location.timestampMillis>0&&kotlin.math.abs(System.currentTimeMillis()-location.timestampMillis)<30000){val placed=location.latitude.isFinite()&&location.longitude.isFinite()&&kotlin.math.abs(location.latitude)<=90&&kotlin.math.abs(location.longitude)<=180&&!(location.latitude==0.0&&location.longitude==0.0);val lat=if(placed)Math.round(location.latitude*100)/100.0 else null;val lon=if(placed)Math.round(location.longitude*100)/100.0 else null;update{it.copy(altitudeMeters=if(location.altitude.isFinite())location.altitude else it.altitudeMeters,latitude=lat?:it.latitude,longitude=lon?:it.longitude)}}}
        override fun onError(exception:Exception){update{it.copy(altitudeMeters=null,latitude=null,longitude=null)};issue("위치 신호",exception)}
    }
    fun addWaypoint(name:String,lat:Double,lon:Double){
        if(closed||!naviReady){issue("경유지",IllegalStateException("NAVI_NOT_READY"));return}
        try{navi!!.addWaypoint(ai.pleos.playground.navi.data.RequestWaypointInfo(lat,lon,name,ai.pleos.playground.navi.constants.WaypointIndex.FIRST,"","","0",""))}
        catch(e:Exception){issue("경유지",e)}
    }
    fun requestRoute(choice:DestinationChoice,id:String){
        if(closed||!naviReady){update{it.copy(routeRequestId=id,routeStatus="FAILED")};return}
        routeTarget=choice to id;update{it.copy(routeRequestId=id,routeStatus="REQUESTING")}
        main.postDelayed({
            if(!closed&&routeTarget?.second==id&&state.routeRequestId==id&&state.routeStatus=="REQUESTING"){
                routeTarget=null
                update{it.copy(routeStatus="UNKNOWN")}
            }
        },20000)
        try{navi!!.requestRoute(RouteInfo(latitude=choice.latitude,longitude=choice.longitude,displayLatitude=null,displayLongitude=null,poiName=choice.name,poiId="",address=choice.address,poiSubId="0"))}
        catch(e:Exception){routeTarget=null;update{it.copy(routeRequestId=id,routeStatus="FAILED")};issue("목적지 요청",e)}
    }
    fun cancelRoute(){check(!closed&&naviReady);navi!!.cancelRoute()}
    private fun subscribeDoors(v:Vehicle){
        v.getDoor().checkDoorPositionCapabilities(onComplete={_,areas->
            if(closed)return@checkDoorPositionCapabilities
            for(area in areas.keys.filter{it==DoorArea(DoorValue.ROW_2_LEFT)||it==DoorArea(DoorValue.ROW_2_RIGHT)}){
                val listener=object:DoorPositionListener{
                    override fun onPositionUpdated(pos:Int?){if(pos==null)return; synchronized(doorPositions){val old=doorPositions.put(area,pos);if(old!=null&&old!=pos)event(if(pos==0)"boarding" else "door_open")}}
                    override fun onFailed(e:Exception)=issue("뒷문",e)
                }
                try{v.getDoor().registerDoorPosition(area,listener);synchronized(cleanup){cleanup+={v.getDoor().unregisterDoorPosition(area,listener)}}
                    v.getDoor().getCurrentDoorPosition(area,{pos->if(pos!=null)synchronized(doorPositions){doorPositions[area]=pos}},{issue("뒷문 읽기",it)})
                }catch(e:Exception){issue("뒷문 구독",e)}
            }
        },onFailed={issue("뒷문 지원 조회",it)})
    }
    private fun subscribeWiper(v:Vehicle){
        v.getWiper().checkWiperStateCapabilities(onComplete={_,areas->
            val area=WindowArea(WindowValue.FRONT_WINDSHIELD)
            if(closed||!areas.containsKey(area))return@checkWiperStateCapabilities
            val listener=object:WiperStateListener{
                override fun onWiperStateUpdated(value:WiperState?){val on=value!=null&&!value.name.contains("OFF")&&!value.name.contains("UNKNOWN");if(on&&!wiperWasOn)event("rain");wiperWasOn=on}
                override fun onFailed(e:Exception)=issue("와이퍼",e)
            }
            try{v.getWiper().registerWiperState(area,listener);synchronized(cleanup){cleanup+={v.getWiper().unregisterWiperState(area,listener)}}}catch(e:Exception){issue("와이퍼 구독",e)}
        },onFailed={issue("와이퍼 지원 조회",it)})
    }
    private fun subscribeTurnSignal(v:Vehicle){
        v.getTurnSignal().checkTurnSignalStateCapabilities(onComplete={config->
            if(closed||!config.accessType.name.contains("READ"))return@checkTurnSignalStateCapabilities
            val listener=object:TurnSignalStateListener{
                override fun onTurnSignalStateUpdated(value:TurnSignalValue?){val name=value?.name ?: "OFF";if(name!=previousTurn&&(name.contains("LEFT")||name.contains("RIGHT")))event(if(name.contains("LEFT"))"turn_left" else "turn_right");previousTurn=name}
                override fun onFailed(e:Exception)=issue("방향지시등",e)
            }
            try{v.getTurnSignal().registerTurnSignalState(listener);synchronized(cleanup){cleanup+={v.getTurnSignal().unregisterTurnSignalState(listener)}}}catch(e:Exception){issue("방향지시등 구독",e)}
        },onFailed={issue("방향지시등 지원 조회",it)})
    }
    private fun subscribeBattery(v:Vehicle){
        v.getEvBattery().checkEvBatteryStateOfChargeCapabilities(onComplete={config->
            if(closed||!config.accessType.name.contains("READ"))return@checkEvBatteryStateOfChargeCapabilities
            val listener=object:EvBatteryStateOfChargeListener{
                override fun onEvBatteryStateOfChargeUpdated(value:Int?){if(value!=null&&value in 0..100)update{it.copy(battery=value)}}
                override fun onFailed(e:Exception)=issue("배터리",e)
            }
            try{v.getEvBattery().registerEvBatteryStateOfCharge(listener);synchronized(cleanup){cleanup+={v.getEvBattery().unregisterEvBatteryStateOfCharge(listener)}};v.getEvBattery().getEvBatteryStateOfCharge({value->if(value!=null&&value in 0..100)update{it.copy(battery=value)}},{issue("배터리 읽기",it)})}catch(e:Exception){issue("배터리 구독",e)}
        },onFailed={issue("배터리 지원 조회",it)})
        v.getEvBattery().checkEvChargeSwitchCapabilities(onComplete={config->
            if(closed||!config.accessType.name.contains("READ"))return@checkEvChargeSwitchCapabilities
            var pending=false
            reads.launch{while(isActive&&!closed){
                if(!pending){pending=true;v.getEvBattery().getEvChargeSwitchState({value->pending=false;if(value!=null){if(value&&!chargeWasOn)event("charging");chargeWasOn=value;update{it.copy(chargingActive=value)}}},{pending=false;issue("충전 상태",it)})}
                delay(2000)
            }}
        },onFailed={issue("충전 지원 조회",it)})
    }
    private fun subscribeDistance(v:Vehicle){
        v.getOdometer().checkCurrentDistanceDrivenCapabilities(onComplete={config->
            if(closed||!config.accessType.name.contains("READ"))return@checkCurrentDistanceDrivenCapabilities
            val listener=object:DistanceDrivenListener{
                override fun onDistanceDrivenUpdated(value:Float?){if(value!=null&&value.isFinite()&&value>=0f)update{it.copy(odometerKm=value)}}
                override fun onFailed(e:Exception)=issue("주행거리",e)
            }
            try{v.getOdometer().registerDistanceDriven(listener);synchronized(cleanup){cleanup+={v.getOdometer().unregisterDistanceDriven(listener)}};v.getOdometer().getCurrentDistanceDriven({value->if(value!=null&&value.isFinite()&&value>=0f)update{it.copy(odometerKm=value)}},{issue("주행거리 읽기",it)})}catch(e:Exception){issue("주행거리 구독",e)}
        },onFailed={issue("주행거리 지원 조회",it)})
    }
    private val propertyCallback=object:CarPropertyManager.CarPropertyEventCallback{
        override fun onChangeEvent(value:CarPropertyValue<*>){
            if(value.status!=CarPropertyValue.STATUS_AVAILABLE){unavailable(value.propertyId);return}
            when(value.propertyId){
                VehiclePropertyIds.GEAR_SELECTION->{val gear=when((value.value as? Number)?.toInt()){VehicleGear.GEAR_PARK->"P";VehicleGear.GEAR_DRIVE->"D";VehicleGear.GEAR_REVERSE->"R";VehicleGear.GEAR_NEUTRAL->"N";else->"—"};val old=state.gear;update{it.copy(gear=gear)};if(!coreStale()&&old!=gear&&gear=="D")event("depart")}
                VehiclePropertyIds.PERF_VEHICLE_SPEED->{val speed=(value.value as? Number)?.toFloat()?.times(3.6f);if(speed!=null&&speed.isFinite())update{it.copy(speedKmh=speed.coerceAtLeast(0f))}}
                VehiclePropertyIds.EV_CHARGE_SWITCH->{val active=value.value as? Boolean;if(active!=null){if(active&&!chargeWasOn)event("charging");chargeWasOn=active;update{it.copy(chargingActive=active)}}}
                VehiclePropertyIds.HVAC_TEMPERATURE_CURRENT->{val temperature=(value.value as? Number)?.toFloat();if(temperature!=null&&temperature.isFinite())update{it.copy(cabinTemperatureC=temperature,cabinTemperatureArea=value.areaId,cabinTemperatureAt=SystemClock.elapsedRealtime())}}
                VehiclePropertyIds.EV_CHARGE_PORT_CONNECTED->{val plugged=value.value as? Boolean;if(plugged!=null){if(plugged&&state.chargingConnected!=true)event("charging");update{it.copy(chargingConnected=plugged)}}}
            }
        }
        override fun onErrorEvent(propertyId:Int,areaId:Int){unavailable(propertyId);Log.w("PliVehicle","VHAL unavailable: $propertyId/$areaId")}
    }
    private fun unavailable(id:Int){when(id){VehiclePropertyIds.HVAC_TEMPERATURE_CURRENT->update{it.copy(cabinTemperatureC=null,cabinTemperatureArea=null,cabinTemperatureAt=0)};VehiclePropertyIds.GEAR_SELECTION->update{it.copy(gear="—")};VehiclePropertyIds.PERF_VEHICLE_SPEED->update{it.copy(speedKmh=null)}}}
    private val uxListener=CarUxRestrictionsManager.OnUxRestrictionsChangedListener{restrictions->update{it.copy(uxRestricted=restrictions.isRequiresDistractionOptimization)}}
    private fun subscribeAaos(connectedCar:Car){
        try{
            val manager=connectedCar.getCarManager(Car.PROPERTY_SERVICE) as CarPropertyManager;propertyManager=manager
            val configurations=manager.propertyList.map{it.propertyId}.toSet()
            val core=listOf(VehiclePropertyIds.GEAR_SELECTION,VehiclePropertyIds.PERF_VEHICLE_SPEED).filter{it in configurations}
            val supported=core+listOf(VehiclePropertyIds.EV_CHARGE_PORT_CONNECTED,VehiclePropertyIds.EV_CHARGE_SWITCH,VehiclePropertyIds.HVAC_TEMPERATURE_CURRENT).filter{it in configurations}
            for(id in supported){
                try{manager.registerCallback(propertyCallback,id,CarPropertyManager.SENSOR_RATE_ONCHANGE)}catch(e:Exception){issue("차량 속도/기어",e)}
            }
            if(VehiclePropertyIds.HVAC_TEMPERATURE_CURRENT in configurations){
                val areas=manager.propertyList.first{it.propertyId==VehiclePropertyIds.HVAC_TEMPERATURE_CURRENT}.areaIds
                reads.launch{for(area in areas)runCatching{manager.getProperty<Any>(VehiclePropertyIds.HVAC_TEMPERATURE_CURRENT,area)}.getOrNull()?.let(propertyCallback::onChangeEvent)}
            }
            // Pleos 2.1's CarPropertyService can retain a dead callback after an APK process restarts.
            // Real VHAL readback keeps the view current while subscriptions recover; no simulated values.
            reads.launch{while(isActive&&!closed){
                // Optional EV data must not serialize the speed/gear polling lane.
                // The emulator can advertise an optional VHAL value without ever
                // completing a synchronous read. Its actual callback is sufficient.
                var complete=core.isNotEmpty()
                val observed=mutableListOf<CarPropertyValue<Any>>()
                for(id in core){
                    val value=runCatching{manager.getProperty<Any>(id,0)}.getOrNull()
                    if(value==null||value.status!=CarPropertyValue.STATUS_AVAILABLE)complete=false
                    if(value!=null)observed+=value
                }
                if(complete){coreCompletedAt=SystemClock.elapsedRealtime();update{it.copy(source="Pleos Vehicle 2.3.2 · AAOS")}}
                observed.forEach(propertyCallback::onChangeEvent)
                delay(1000)
            }}
        }catch(e:Exception){issue("차량 속도/기어",e)}
        try{val manager=connectedCar.getCarManager(Car.CAR_UX_RESTRICTION_SERVICE) as CarUxRestrictionsManager;uxManager=manager;manager.registerListener(uxListener);update{it.copy(uxRestricted=manager.currentCarUxRestrictions.isRequiresDistractionOptimization)}}catch(e:Exception){issue("UX 상태",e)}
    }
    private val naviListener=object:NaviHelperEventListener{
        override fun onRouteStateInfo(info:RouteStateInfo){guiding=info.naviMode in setOf(ai.pleos.playground.navi.constants.NaviMode.ROUTE_GUIDING,ai.pleos.playground.navi.constants.NaviMode.SIMULATION_GUIDING);update{if(guiding)it.copy(routeActive=true)else it.copy(routeActive=false,destination=null,destinationLatitude=null,destinationLongitude=null,minutesRemaining=null)};if(guiding)navi?.getDestinationInfo()}
        override fun onRouteStarted(info:RouteStartInfo){navi?.getRouteStateInfo();navi?.getDestinationInfo()}
        override fun onRoutingCompleted(){navi?.getRouteStateInfo();navi?.getDestinationInfo()}
        override fun onRouteCancelled(){guiding=false;routeTarget=null;update{it.copy(routeActive=false,routeStatus="CANCELLED",destination=null,destinationLatitude=null,destinationLongitude=null,minutesRemaining=null)}}
        override fun onRouteEnded(){guiding=false;update{it.copy(routeActive=false,destination=null,destinationLatitude=null,destinationLongitude=null,minutesRemaining=null)}}
        override fun onDestinationInfo(info:DestinationInfo){if(!guiding)return;val target=routeTarget;val confirmed=guiding&&target!=null&&kotlin.math.abs(target.first.latitude-info.latitude)<.001&&kotlin.math.abs(target.first.longitude-info.longitude)<.001;update{it.copy(destination=info.name.takeIf(String::isNotBlank),destinationLatitude=info.latitude,destinationLongitude=info.longitude,minutesRemaining=ceil(info.remainTime/60.0).toInt().coerceAtLeast(0),routeRequestId=target?.second?:it.routeRequestId,routeStatus=if(confirmed)"CONFIRMED"else it.routeStatus)};if(guiding&&info.remainTime in 1..120&&!nearArrival){nearArrival=true;event("nearby")}else if(info.remainTime>180)nearArrival=false}
        override fun onDestinationChanged(){navi?.getDestinationInfo()}
        override fun onDestinationArrived(info:DestinationArrivedInfo){event("arrive")}
        override fun onDrivingInfo(info:DrivingInfo){navi?.getDestinationInfo()}
        override fun onError(errorCode:NaviErrorCode){if(routeTarget!=null){routeTarget=null;update{it.copy(routeStatus="FAILED")}};Log.w("PliVehicle","Navi: $errorCode")}
    }
    fun close(){
        closed=true
        reads.cancel()
        main.removeCallbacksAndMessages(null)
        onState(state.copy(connected=false,gear="—",speedKmh=null,source="차량 연결 종료"))
        Thread({
            synchronized(cleanup){cleanup.reversed().forEach{runCatching(it)};cleanup.clear()}
            runCatching{propertyManager?.unregisterCallback(propertyCallback)};runCatching{uxManager?.unregisterListener()}
            runCatching{car?.disconnect()};runCatching{navi?.removeListener(naviListener);navi?.release()};runCatching{vehicle?.release()}
            runCatching{fused?.unregisterFusedLocationCallback(locationListener);fused?.release()}
        },"pli-sdk-release").apply{isDaemon=true;start()}
    }
}
