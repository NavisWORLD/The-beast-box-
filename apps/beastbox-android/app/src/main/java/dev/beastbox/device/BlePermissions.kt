package dev.beastbox.device

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build

object BlePermissions {
    /** Runtime permissions needed before the GATT server / advertiser may be touched. */
    fun required(): Array<String> = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        arrayOf(Manifest.permission.BLUETOOTH_ADVERTISE, Manifest.permission.BLUETOOTH_CONNECT)
    } else {
        emptyArray() // BLUETOOTH / BLUETOOTH_ADMIN are install-time on Android 8-11.
    }

    /** Asked for alongside, but not required: without it the foreground notification is hidden. */
    fun optional(): Array<String> = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        arrayOf(Manifest.permission.POST_NOTIFICATIONS)
    } else emptyArray()

    fun missing(context: Context): List<String> =
        required().filter { context.checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }

    fun granted(context: Context): Boolean = missing(context).isEmpty()
}
