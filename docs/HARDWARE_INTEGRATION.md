# Hardware and Industrial Gateway Integration

## Sensor ingestion

Endpoint:

```text
POST /api/hardware/readings
```

Header:

```text
X-Device-Key: <DEVICE_API_KEY from backend/.env>
```

Example body:

```json
{
  "machine_id": "M-001",
  "temperature": 78.4,
  "vibration": 0.82,
  "pressure": 31.2,
  "rpm": 1450,
  "torque": 52.0,
  "power": 12.8,
  "operating_hours": 6280,
  "tool_wear": 118,
  "source": "edge-gateway-01"
}
```

The backend validates and stores the reading, performs anomaly detection and failure-risk inference, updates the machine state, creates an alert when required, and returns the analysis.

## Command layer

Supported command names:

- `reject_product`
- `stop_machine`
- `start_machine`
- `pause_conveyor`
- `resume_conveyor`
- `request_inspection`
- `trigger_warning_light`
- `open_maintenance_ticket`

Commands are persisted and processed by the local industrial adapter. In the cloud/plant phase, replace the adapter with an MQTT, OPC-UA, Modbus, or vendor-specific gateway that confirms device execution.

## ESP32 example

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

void sendReading() {
  HTTPClient http;
  http.begin("http://GATEWAY_IP:8000/api/hardware/readings");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", "forgemind-local-device-key");
  String payload = "{\"machine_id\":\"M-001\",\"temperature\":78.4,\"vibration\":0.82,\"pressure\":31.2,\"rpm\":1450,\"torque\":52,\"power\":12.8}";
  int statusCode = http.POST(payload);
  String response = http.getString();
  http.end();
}
```

## Production safeguards

Before controlling physical equipment:

- Use HTTPS or a private industrial network.
- Give each gateway its own revocable credential.
- Add nonce or signature validation where practical.
- Add device heartbeats, retries, idempotency, and command acknowledgement.
- Enforce limits at the PLC and safety-controller level.
- Keep emergency stops and safety interlocks independent from this application.
- Validate all models and thresholds using the target plant’s equipment and operating conditions.
