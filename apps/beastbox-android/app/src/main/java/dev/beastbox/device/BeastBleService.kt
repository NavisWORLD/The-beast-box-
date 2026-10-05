package dev.beastbox.device

import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothGattServer
import android.bluetooth.BluetoothGattServerCallback
import android.bluetooth.BluetoothGattService
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.AdvertiseCallback
import android.bluetooth.le.AdvertiseData
import android.bluetooth.le.AdvertiseSettings
import android.bluetooth.le.BluetoothLeAdvertiser
import android.content.Context
import android.content.BroadcastReceiver
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.graphics.drawable.Icon
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.ParcelUuid
import android.util.Log
import java.nio.charset.StandardCharsets
import java.util.concurrent.ConcurrentHashMap

/**
 * Foreground service that makes the phone a BLE peripheral called "Beast Box · <beast name>",
 * advertising Beast Box's own random service UUID and hosting its GATT characteristics.
 *
 * Every Bluetooth call below runs only after [BlePermissions.granted] has been checked in
 * [startBle] (and the service is never started without it), hence the class-level suppression.
 */
@SuppressLint("MissingPermission")
class BeastBleService : Service() {

    private val main = Handler(Looper.getMainLooper())
    private lateinit var settings: BeastSettings
    private var adapter: BluetoothAdapter? = null
    private var advertiser: BluetoothLeAdvertiser? = null
    private var gattServer: BluetoothGattServer? = null
    private var stateChar: BluetoothGattCharacteristic? = null
    private val connected = ConcurrentHashMap.newKeySet<BluetoothDevice>()
    private val subscribers = ConcurrentHashMap.newKeySet<BluetoothDevice>()
    private var advertising = false
    private var advertisedName: String? = null
    private var running = false
    /** Set if the renamed GAP name didn't fit (adapter rename not applied yet); use service-data name instead. */
    private var nameFallback = false
    private var advertisedWithAdapterName = false

    private val stateListener: (BeastState) -> Unit = { state -> onStateChanged(state) }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        settings = BeastSettings(this)
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            shutdown()
            stopSelf()
            return START_NOT_STICKY
        }
        if (!BlePermissions.granted(this)) {
            BeastHub.setStatus(AdvertisingStatus.Failed("Bluetooth permissions not granted"))
            stopSelf()
            return START_NOT_STICKY
        }
        goForeground(getString(R.string.notif_starting))
        if (!running) startBle()
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        shutdown()
        super.onDestroy()
    }

    // ---- lifecycle ----------------------------------------------------------------------------

    private fun startBle() {
        val manager = getSystemService(BluetoothManager::class.java) ?: return fail("No Bluetooth service")
        val bt = manager.adapter ?: return fail("This phone has no Bluetooth adapter")
        if (!bt.isEnabled) return fail("Bluetooth is off")
        val adv = bt.bluetoothLeAdvertiser
        if (adv == null || !bt.isMultipleAdvertisementSupported) {
            return fail("This phone can't advertise as a BLE peripheral")
        }
        adapter = bt
        advertiser = adv
        running = true
        nameFallback = false
        BeastHub.setStatus(AdvertisingStatus.Starting)
        BeastHub.addStateListener(stateListener)
        registerBluetoothStateReceiver()

        val server = try {
            manager.openGattServer(this, gattCallback)
        } catch (e: SecurityException) {
            null
        } ?: return fail("Couldn't open a GATT server")
        gattServer = server
        // Advertising starts from onServiceAdded once the service is registered.
        if (!server.addService(buildService())) fail("Couldn't register the Beast Box GATT service")
    }

    private fun shutdown() {
        if (!running && gattServer == null) return
        running = false
        BeastHub.removeStateListener(stateListener)
        unregisterBluetoothStateReceiver()
        main.removeCallbacksAndMessages(null)
        try {
            advertiser?.stopAdvertising(advertiseCallback)
        } catch (e: Exception) { Log.w(TAG, "stopAdvertising", e) } // SecurityException / adapter turning off
        advertising = false
        try {
            gattServer?.clearServices()
            gattServer?.close()
        } catch (e: Exception) { Log.w(TAG, "close gatt", e) }
        gattServer = null
        connected.clear()
        subscribers.clear()
        restoreAdapterName()
        BeastHub.setStatus(AdvertisingStatus.Off)
        stopForegroundCompat()
    }

    private fun fail(reason: String) {
        Log.w(TAG, reason)
        shutdown()
        BeastHub.setStatus(AdvertisingStatus.Failed(reason))
        stopSelf()
    }

    // ---- GATT ---------------------------------------------------------------------------------

    private fun buildService(): BluetoothGattService {
        val service = BluetoothGattService(BeastUuids.SERVICE, BluetoothGattService.SERVICE_TYPE_PRIMARY)
        val state = BluetoothGattCharacteristic(
            BeastUuids.STATE,
            BluetoothGattCharacteristic.PROPERTY_READ or BluetoothGattCharacteristic.PROPERTY_NOTIFY,
            BluetoothGattCharacteristic.PERMISSION_READ,
        )
        state.addDescriptor(
            BluetoothGattDescriptor(
                BeastUuids.CCCD,
                BluetoothGattDescriptor.PERMISSION_READ or BluetoothGattDescriptor.PERMISSION_WRITE,
            ),
        )
        val name = BluetoothGattCharacteristic(
            BeastUuids.NAME,
            BluetoothGattCharacteristic.PROPERTY_READ,
            BluetoothGattCharacteristic.PERMISSION_READ,
        )
        val command = BluetoothGattCharacteristic(
            BeastUuids.COMMAND,
            BluetoothGattCharacteristic.PROPERTY_WRITE or BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE,
            BluetoothGattCharacteristic.PERMISSION_WRITE,
        )
        service.addCharacteristic(state)
        service.addCharacteristic(name)
        service.addCharacteristic(command)
        stateChar = state
        return service
    }

    private val gattCallback = object : BluetoothGattServerCallback() {
        override fun onServiceAdded(status: Int, service: BluetoothGattService) {
            main.post {
                if (!running) return@post
                if (status == BluetoothGatt.GATT_SUCCESS) beginAdvertising(BeastHub.state)
                else fail("GATT service registration failed ($status)")
            }
        }

        override fun onConnectionStateChange(device: BluetoothDevice, status: Int, newState: Int) {
            if (newState == BluetoothProfile.STATE_CONNECTED) connected += device
            else { connected -= device; subscribers -= device }
            main.post { publishStatus() }
        }

        override fun onCharacteristicReadRequest(
            device: BluetoothDevice, requestId: Int, offset: Int, characteristic: BluetoothGattCharacteristic,
        ) {
            val value = when (characteristic.uuid) {
                BeastUuids.STATE -> BeastProtocol.encodeState(BeastHub.state)
                BeastUuids.NAME -> BeastProtocol.encodeName(BeastHub.state)
                else -> null
            }
            val server = gattServer ?: return
            when {
                value == null -> server.sendResponse(device, requestId, BluetoothGatt.GATT_READ_NOT_PERMITTED, offset, null)
                offset > value.size -> server.sendResponse(device, requestId, BluetoothGatt.GATT_INVALID_OFFSET, offset, null)
                else -> server.sendResponse(device, requestId, BluetoothGatt.GATT_SUCCESS, offset, value.copyOfRange(offset, value.size))
            }
        }

        override fun onCharacteristicWriteRequest(
            device: BluetoothDevice, requestId: Int, characteristic: BluetoothGattCharacteristic,
            preparedWrite: Boolean, responseNeeded: Boolean, offset: Int, value: ByteArray?,
        ) {
            val server = gattServer ?: return
            val status = when {
                characteristic.uuid != BeastUuids.COMMAND -> BluetoothGatt.GATT_WRITE_NOT_PERMITTED
                preparedWrite || offset != 0 -> BluetoothGatt.GATT_REQUEST_NOT_SUPPORTED
                else -> {
                    val frame = BeastProtocol.decodeCommand(value)
                    if (frame == null) APP_ERROR_UNKNOWN_COMMAND
                    else {
                        BeastHub.commandFromBle(frame, sourceLabel(device))
                        BluetoothGatt.GATT_SUCCESS
                    }
                }
            }
            if (responseNeeded) server.sendResponse(device, requestId, status, 0, null)
        }

        override fun onDescriptorReadRequest(
            device: BluetoothDevice, requestId: Int, offset: Int, descriptor: BluetoothGattDescriptor,
        ) {
            val value = if (device in subscribers) BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
            else BluetoothGattDescriptor.DISABLE_NOTIFICATION_VALUE
            gattServer?.sendResponse(device, requestId, BluetoothGatt.GATT_SUCCESS, 0, value)
        }

        override fun onDescriptorWriteRequest(
            device: BluetoothDevice, requestId: Int, descriptor: BluetoothGattDescriptor,
            preparedWrite: Boolean, responseNeeded: Boolean, offset: Int, value: ByteArray?,
        ) {
            var status = BluetoothGatt.GATT_SUCCESS
            if (descriptor.uuid == BeastUuids.CCCD) {
                when {
                    value contentEquals BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE -> subscribers += device
                    value contentEquals BluetoothGattDescriptor.DISABLE_NOTIFICATION_VALUE -> subscribers -= device
                    else -> status = BluetoothGatt.GATT_REQUEST_NOT_SUPPORTED
                }
            } else status = BluetoothGatt.GATT_WRITE_NOT_PERMITTED
            if (responseNeeded) gattServer?.sendResponse(device, requestId, status, 0, null)
        }
    }

    private fun onStateChanged(state: BeastState) {
        if (!running) return
        notifySubscribers(BeastProtocol.encodeState(state))
        val wanted = BeastProtocol.advertisedName(state.shownName)
        if (advertising && wanted != advertisedName) restartAdvertising(state)
    }

    @Suppress("DEPRECATION")
    private fun notifySubscribers(value: ByteArray) {
        val server = gattServer ?: return
        val characteristic = stateChar ?: return
        for (device in subscribers) {
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    server.notifyCharacteristicChanged(device, characteristic, false, value)
                } else {
                    characteristic.value = value
                    server.notifyCharacteristicChanged(device, characteristic, false)
                }
            } catch (e: Exception) { Log.w(TAG, "notify", e) }
        }
    }

    // ---- advertising --------------------------------------------------------------------------

    private fun beginAdvertising(state: BeastState) {
        val adv = advertiser ?: return
        val name = BeastProtocol.advertisedName(state.shownName)
        val renamed = settings.renameAdapter && !nameFallback && applyAdapterName(name)
        // Delay lets the controller pick up the new adapter name before it goes into the scan response.
        main.postDelayed({
            if (!running) return@postDelayed
            val advSettings = AdvertiseSettings.Builder()
                .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
                .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_MEDIUM)
                .setConnectable(true)
                .setTimeout(0)
                .build()
            // Primary packet: flags + Beast Box's own 128-bit service UUID (21 of 31 bytes).
            val data = AdvertiseData.Builder()
                .setIncludeDeviceName(false)
                .setIncludeTxPowerLevel(false)
                .addServiceUuid(ParcelUuid(BeastUuids.SERVICE))
                .build()
            // Scan response: the "Beast Box · <name>" GAP name, or (if renaming is off) a short name as service data.
            val scan = AdvertiseData.Builder().setIncludeTxPowerLevel(false).apply {
                if (renamed) setIncludeDeviceName(true)
                else {
                    setIncludeDeviceName(false)
                    val shortName = BeastProtocol.truncateUtf8(BeastProtocol.sanitizeName(state.shownName).ifBlank { "Beast Box" }, 11)
                    addServiceData(ParcelUuid(BeastUuids.SERVICE), shortName.toByteArray(StandardCharsets.UTF_8))
                }
            }.build()
            try {
                adv.startAdvertising(advSettings, data, scan, advertiseCallback)
                advertisedName = name
                advertisedWithAdapterName = renamed
            } catch (e: SecurityException) {
                fail("Advertise permission was revoked")
            } catch (e: IllegalStateException) {
                fail("Bluetooth is off")
            }
        }, if (renamed) RENAME_SETTLE_MS else 0L)
    }

    private fun restartAdvertising(state: BeastState) {
        try { advertiser?.stopAdvertising(advertiseCallback) } catch (e: Exception) { Log.w(TAG, "stop", e) }
        advertising = false
        beginAdvertising(state)
    }

    private val advertiseCallback = object : AdvertiseCallback() {
        override fun onStartSuccess(settingsInEffect: AdvertiseSettings) {
            main.post {
                if (!running) return@post
                advertising = true
                publishStatus()
                // The beast may have been renamed while this advert was starting.
                if (BeastProtocol.advertisedName(BeastHub.state.shownName) != advertisedName) restartAdvertising(BeastHub.state)
            }
        }

        override fun onStartFailure(errorCode: Int) {
            val reason = when (errorCode) {
                AdvertiseCallback.ADVERTISE_FAILED_DATA_TOO_LARGE -> "advert too large (shorten the beast name)"
                AdvertiseCallback.ADVERTISE_FAILED_TOO_MANY_ADVERTISERS -> "too many apps are advertising"
                AdvertiseCallback.ADVERTISE_FAILED_ALREADY_STARTED -> "already advertising"
                AdvertiseCallback.ADVERTISE_FAILED_FEATURE_UNSUPPORTED -> "BLE advertising unsupported on this phone"
                else -> "internal error $errorCode"
            }
            main.post {
                if (!running) return@post
                when {
                    errorCode == AdvertiseCallback.ADVERTISE_FAILED_ALREADY_STARTED -> { advertising = true; publishStatus() }
                    errorCode == AdvertiseCallback.ADVERTISE_FAILED_DATA_TOO_LARGE && advertisedWithAdapterName && !nameFallback -> {
                        Log.w(TAG, "GAP name too long for the scan response; falling back to service-data name")
                        nameFallback = true
                        beginAdvertising(BeastHub.state)
                    }
                    else -> fail("Advertising failed: $reason")
                }
            }
        }
    }

    // ---- Bluetooth turned off underneath us -------------------------------------------------------

    private var btStateReceiver: BroadcastReceiver? = null

    private fun registerBluetoothStateReceiver() {
        if (btStateReceiver != null) return
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context, intent: Intent) {
                val st = intent.getIntExtra(BluetoothAdapter.EXTRA_STATE, BluetoothAdapter.ERROR)
                if (st == BluetoothAdapter.STATE_TURNING_OFF || st == BluetoothAdapter.STATE_OFF) {
                    fail("Bluetooth was turned off")
                }
            }
        }
        val filter = IntentFilter(BluetoothAdapter.ACTION_STATE_CHANGED)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(receiver, filter)
        }
        btStateReceiver = receiver
    }

    private fun unregisterBluetoothStateReceiver() {
        btStateReceiver?.let { runCatching { unregisterReceiver(it) } }
        btStateReceiver = null
    }

    // ---- phone Bluetooth name ------------------------------------------------------------------

    private fun applyAdapterName(name: String): Boolean {
        val bt = adapter ?: return false
        return try {
            val current = bt.name
            if (settings.savedAdapterName == null && current != null && !current.startsWith(BeastProtocol.NAME_PREFIX)) {
                settings.savedAdapterName = current
            }
            current == name || bt.setName(name)
        } catch (e: SecurityException) {
            false
        }
    }

    private fun restoreAdapterName() {
        val original = settings.savedAdapterName ?: return
        try {
            if (adapter?.setName(original) == true) settings.savedAdapterName = null
        } catch (e: SecurityException) { Log.w(TAG, "restore name", e) }
    }

    // ---- notification -------------------------------------------------------------------------

    private fun publishStatus() {
        if (!running) return
        val status = if (advertising) AdvertisingStatus.Advertising(advertisedName ?: "Beast Box", connected.size)
        else AdvertisingStatus.Starting
        BeastHub.setStatus(status)
        val text = when (status) {
            is AdvertisingStatus.Advertising -> getString(R.string.notif_advertising, status.name, status.clients)
            else -> getString(R.string.notif_starting)
        }
        getSystemService(NotificationManager::class.java)?.notify(NOTIFICATION_ID, buildNotification(text))
    }

    private fun createChannel() {
        val channel = NotificationChannel(CHANNEL_ID, getString(R.string.channel_name), NotificationManager.IMPORTANCE_LOW)
        channel.description = getString(R.string.channel_description)
        getSystemService(NotificationManager::class.java)?.createNotificationChannel(channel)
    }

    private fun buildNotification(text: String): Notification {
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val stop = PendingIntent.getService(
            this, 1, Intent(this, BeastBleService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_beastbox)
            .setContentTitle(getString(R.string.notif_title))
            .setContentText(text)
            .setOngoing(true)
            .setContentIntent(open)
            .addAction(
                Notification.Action.Builder(
                    Icon.createWithResource(this, R.drawable.ic_stat_beastbox), getString(R.string.notif_stop), stop,
                ).build(),
            )
            .build()
    }

    private fun goForeground(text: String) {
        val notification = buildNotification(text)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun stopForegroundCompat() {
        stopForeground(STOP_FOREGROUND_REMOVE)
    }

    companion object {
        private const val TAG = "BeastBoxBle"
        private const val CHANNEL_ID = "beastbox_ble"
        private const val NOTIFICATION_ID = 0xBB01
        private const val RENAME_SETTLE_MS = 700L
        /** ATT application error (0x80): the command frame wasn't feed / play / talk / attack. */
        const val APP_ERROR_UNKNOWN_COMMAND = 0x80
        const val ACTION_START = "dev.beastbox.device.action.START"
        const val ACTION_STOP = "dev.beastbox.device.action.STOP"

        fun start(context: Context) {
            context.startForegroundService(Intent(context, BeastBleService::class.java).setAction(ACTION_START))
        }

        fun stop(context: Context) {
            context.startService(Intent(context, BeastBleService::class.java).setAction(ACTION_STOP))
        }

        /** Masks the client address before it reaches page JavaScript. */
        @SuppressLint("HardwareIds")
        fun sourceLabel(device: BluetoothDevice): String {
            val addr = device.address ?: return "ble"
            return "ble:" + addr.takeLast(5)
        }
    }
}
