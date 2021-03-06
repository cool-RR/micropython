# Test BLE GAP connect/disconnect

from micropython import const
import time, machine, bluetooth

TIMEOUT_MS = 5000

_IRQ_CENTRAL_CONNECT = const(1 << 0)
_IRQ_CENTRAL_DISCONNECT = const(1 << 1)
_IRQ_PERIPHERAL_CONNECT = const(1 << 6)
_IRQ_PERIPHERAL_DISCONNECT = const(1 << 7)
_IRQ_GATTC_SERVICE_RESULT = const(1 << 8)

UUID_A = bluetooth.UUID(0x180D)
UUID_B = bluetooth.UUID("A5A5A5A5-FFFF-9999-1111-5A5A5A5A5A5A")
SERVICE_A = (
    UUID_A,
    (),
)
SERVICE_B = (
    UUID_B,
    (),
)
SERVICES = (SERVICE_A, SERVICE_B)

last_event = None
last_data = None
num_service_result = 0


def irq(event, data):
    global last_event, last_data, num_service_result
    last_event = event
    last_data = data
    if event == _IRQ_CENTRAL_CONNECT:
        print("_IRQ_CENTRAL_CONNECT")
    elif event == _IRQ_CENTRAL_DISCONNECT:
        print("_IRQ_CENTRAL_DISCONNECT")
    elif event == _IRQ_PERIPHERAL_CONNECT:
        print("_IRQ_PERIPHERAL_CONNECT")
    elif event == _IRQ_PERIPHERAL_DISCONNECT:
        print("_IRQ_PERIPHERAL_DISCONNECT")
    elif event == _IRQ_GATTC_SERVICE_RESULT:
        if data[3] == UUID_A or data[3] == UUID_B:
            print("_IRQ_GATTC_SERVICE_RESULT", data[3])
            num_service_result += 1


def wait_for_event(event, timeout_ms):
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
        if isinstance(event, int):
            if last_event == event:
                break
        elif event():
            break
        machine.idle()


# Acting in peripheral role.
def instance0():
    multitest.globals(BDADDR=ble.config("mac"))
    ble.gatts_register_services(SERVICES)
    print("gap_advertise")
    ble.gap_advertise(20_000, b"\x02\x01\x06\x04\xffMPY")
    multitest.next()
    try:
        wait_for_event(_IRQ_CENTRAL_CONNECT, TIMEOUT_MS)
        wait_for_event(_IRQ_CENTRAL_DISCONNECT, TIMEOUT_MS)
    finally:
        ble.active(0)


# Acting in central role.
def instance1():
    multitest.next()
    try:
        # Connect to peripheral and then disconnect.
        print("gap_connect")
        ble.gap_connect(0, BDADDR)
        wait_for_event(_IRQ_PERIPHERAL_CONNECT, TIMEOUT_MS)
        if last_event != _IRQ_PERIPHERAL_CONNECT:
            return
        conn_handle, _, _ = last_data

        # Discover services.
        ble.gattc_discover_services(conn_handle)
        wait_for_event(lambda: num_service_result == 2, TIMEOUT_MS)

        # Disconnect from peripheral.
        print("gap_disconnect:", ble.gap_disconnect(conn_handle))
        wait_for_event(_IRQ_PERIPHERAL_DISCONNECT, TIMEOUT_MS)
    finally:
        ble.active(0)


ble = bluetooth.BLE()
ble.active(1)
ble.irq(irq)
