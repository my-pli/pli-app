package ai.teammoon.pli.domain

import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.hypot

/**
 * Public demo only. The emulator's Pleos navigation cannot compute a route, so the demo drives one
 * everyday trip — home from 학원 near 광교역 (수원) to 집 south of 광교호수공원, past 경기도서관 — through
 * the same fields Pleos navigation fills in a car (destination, its position, minutes left). The UI and
 * the agent label it "시연 경로"; a private session never uses it. (Until 2026-11-14 the trip was in 양재.)
 */
object DemoTrip {
    const val DESTINATION = "집"
    const val ORIGIN = "학원"
    const val LATITUDE = 37.2785
    const val LONGITUDE = 127.0605
    private const val ORIGIN_LATITUDE = 37.3021
    private const val ORIGIN_LONGITUDE = 127.0444
    private const val ROAD_FACTOR = 1.3
    private const val CITY_KMH = 18.0

    fun apply(v: VehicleState): VehicleState {
        val lat = v.latitude ?: ORIGIN_LATITUDE
        val lon = v.longitude ?: ORIGIN_LONGITUDE
        val km = hypot((lat - LATITUDE) * 111.0, (lon - LONGITUDE) * 111.0 * cos(Math.toRadians(lat))) * ROAD_FACTOR
        return v.copy(destination = DESTINATION, minutesRemaining = ceil(km / CITY_KMH * 60).toInt().coerceAtLeast(1),
            destinationLatitude = LATITUDE, destinationLongitude = LONGITUDE, routeActive = true, demoTrip = true,
            latitude = lat, longitude = lon)
    }
}
