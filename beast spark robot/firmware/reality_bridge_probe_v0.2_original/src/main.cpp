#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include <BH1750.h>
#include <Adafruit_BME280.h>
#include <Adafruit_ICM42688.h>
#include <MAX30105.h>
#include <TinyGPS++.h>
#include "driver/i2s.h"

// Reality Bridge Probe v0.2 reference firmware
// SOFTWARE IMPLEMENTED. Physical probe qualification is not yet published.
// I2C: SDA 8 / SCL 9. I2S: BCLK 12 / WS 13 / DIN 14. GNSS UART: RX 17 / TX 18.
// INMP441 reference wiring assumes L/R tied LOW (left slot).

static constexpr int SDA_PIN=8, SCL_PIN=9;
static constexpr int I2S_BCLK_PIN=12, I2S_WS_PIN=13, I2S_DATA_PIN=14;
static constexpr int GNSS_RX_PIN=17, GNSS_TX_PIN=18;
static constexpr uint32_t PACKET_MS=100;
static constexpr int AUDIO_RATE=16000;
static constexpr size_t AUDIO_SAMPLES=256;
const char* AP_SSID="RealityBridge-Probe";
const char* AP_PASS="change-this-password";

WebSocketsServer ws(81);
BH1750 luxSensor;
Adafruit_BME280 bme;
Adafruit_ICM42688 imu;
MAX30105 ppg;
TinyGPSPlus gps;
HardwareSerial GNSS(1);
bool hasLux=false,hasBme=false,hasImu=false,hasPpg=false,hasMic=false;
uint32_t lastPacket=0;
float audioNoiseFloor=0.0025f;

bool initMicrophone(){
  i2s_config_t cfg={};
  cfg.mode=(i2s_mode_t)(I2S_MODE_MASTER|I2S_MODE_RX);
  cfg.sample_rate=AUDIO_RATE;
  cfg.bits_per_sample=I2S_BITS_PER_SAMPLE_32BIT;
  cfg.channel_format=I2S_CHANNEL_FMT_ONLY_LEFT;
  cfg.communication_format=I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags=ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count=4;
  cfg.dma_buf_len=256;
  cfg.use_apll=false;
  cfg.tx_desc_auto_clear=false;
  cfg.fixed_mclk=0;
  i2s_pin_config_t pins={};
#if ESP_IDF_VERSION_MAJOR >= 4
  pins.mck_io_num=I2S_PIN_NO_CHANGE;
#endif
  pins.bck_io_num=I2S_BCLK_PIN;
  pins.ws_io_num=I2S_WS_PIN;
  pins.data_out_num=I2S_PIN_NO_CHANGE;
  pins.data_in_num=I2S_DATA_PIN;
  if(i2s_driver_install(I2S_NUM_0,&cfg,0,nullptr)!=ESP_OK) return false;
  if(i2s_set_pin(I2S_NUM_0,&pins)!=ESP_OK){i2s_driver_uninstall(I2S_NUM_0);return false;}
  i2s_zero_dma_buffer(I2S_NUM_0);
  return true;
}

float readAudioRms(){
  if(!hasMic) return 0.0f;
  int32_t samples[AUDIO_SAMPLES]; size_t bytesRead=0;
  esp_err_t ok=i2s_read(I2S_NUM_0,samples,sizeof(samples),&bytesRead,8/portTICK_PERIOD_MS);
  if(ok!=ESP_OK||bytesRead<sizeof(int32_t)*16) return 0.0f;
  size_t n=bytesRead/sizeof(int32_t); double mean=0.0;
  for(size_t i=0;i<n;i++) mean+=(double)(samples[i]>>8); mean/=(double)n;
  double energy=0.0;
  for(size_t i=0;i<n;i++){double v=(double)(samples[i]>>8)-mean;energy+=v*v;}
  double rms=sqrt(energy/(double)n);
  float normalized=(float)(rms/8388608.0);
  return constrain(normalized-audioNoiseFloor,0.0f,1.0f);
}

float calibrateAudioNoiseFloor(uint32_t durationMs=1800){
  uint32_t start=millis(); double sum=0.0; uint32_t n=0; audioNoiseFloor=0.0f;
  while(millis()-start<durationMs){float v=readAudioRms();sum+=v;n++;delay(10);}
  audioNoiseFloor=n?(float)(sum/n)*1.25f:0.0025f;
  audioNoiseFloor=constrain(audioNoiseFloor,0.0001f,0.08f); return audioNoiseFloor;
}
void pollGnss(){while(GNSS.available())gps.encode(GNSS.read());}

void emitSelfTest(){
  StaticJsonDocument<768>d; d["type"]="selftest"; d["firmware"]="0.2.0"; d["millis"]=millis(); d["wifiAp"]=WiFi.softAPIP().toString();
  JsonObject s=d.createNestedObject("sensors"); s["lux"]=hasLux;s["bme280"]=hasBme;s["imu"]=hasImu;s["ppg"]=hasPpg;s["microphone"]=hasMic;s["gnssStreamSeen"]=gps.charsProcessed()>0;
  d["audioNoiseFloor"]=audioNoiseFloor; d["heapFree"]=ESP.getFreeHeap(); String out;serializeJson(d,out);Serial.println(out);
}

void handleSerialCommands(){
  if(!Serial.available())return; String cmd=Serial.readStringUntil('\n'); cmd.trim();cmd.toUpperCase();
  if(cmd=="SELFTEST"||cmd=="STATUS")emitSelfTest();
  else if(cmd=="CAL_AUDIO"){Serial.println("{\"type\":\"calibration\",\"stage\":\"audio\",\"status\":\"starting\"}");float floor=calibrateAudioNoiseFloor();StaticJsonDocument<160>d;d["type"]="calibration";d["stage"]="audio";d["status"]="complete";d["noiseFloor"]=floor;String out;serializeJson(d,out);Serial.println(out);}
  else if(cmd=="HELP")Serial.println("Reality Bridge commands: SELFTEST | CAL_AUDIO | STATUS | HELP");
}

void setup(){
  Serial.begin(115200);delay(350);Wire.begin(SDA_PIN,SCL_PIN);
  hasLux=luxSensor.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
  hasBme=bme.begin(0x76)||bme.begin(0x77);
  hasImu=imu.begin_I2C(0x68,&Wire)||imu.begin_I2C(0x69,&Wire);
  hasPpg=ppg.begin(Wire,I2C_SPEED_FAST);if(hasPpg)ppg.setup(60,4,2,100,411,4096);
  hasMic=initMicrophone(); GNSS.begin(9600,SERIAL_8N1,GNSS_RX_PIN,GNSS_TX_PIN);
  WiFi.mode(WIFI_AP);WiFi.softAP(AP_SSID,AP_PASS);ws.begin();
  Serial.printf("Reality Bridge Probe v0.2 IP %s websocket :81\n",WiFi.softAPIP().toString().c_str()); emitSelfTest();
}

void loop(){
  ws.loop();pollGnss();handleSerialCommands();uint32_t now=millis();if(now-lastPacket<PACKET_MS)return;lastPacket=now;
  float lux=hasLux?luxSensor.readLightLevel():0.0f,tempC=hasBme?bme.readTemperature():0.0f,humidity=hasBme?bme.readHumidity():0.0f,pressure=hasBme?bme.readPressure()/100.0f:0.0f;
  float motion=0.0f,heading=0.0f;
  if(hasImu){sensors_event_t accel,gyro,temp;imu.getEvent(&accel,&gyro,&temp);motion=min(1.0f,sqrtf(accel.acceleration.x*accel.acceleration.x+accel.acceleration.y*accel.acceleration.y+accel.acceleration.z*accel.acceleration.z)/30.0f);heading=fmodf(atan2f(accel.acceleration.y,accel.acceleration.x)*180.0f/PI+360.0f,360.0f);}
  uint32_t ir=hasPpg?ppg.getIR():0,red=hasPpg?ppg.getRed():0; float audioRms=readAudioRms();
  StaticJsonDocument<896>d;d["t"]=now;d["lux"]=lux;d["motion"]=motion;d["audioRms"]=audioRms;d["temperatureC"]=tempC;d["humidityPct"]=humidity;d["pressureHpa"]=pressure;d["ppgIr"]=ir;d["ppgRed"]=red;d["heading"]=heading;d["firmware"]="0.2.0";
  if(gps.location.isValid()){d["latitude"]=gps.location.lat();d["longitude"]=gps.location.lng();}else{d["latitude"]=nullptr;d["longitude"]=nullptr;}
  d["altitudeM"]=gps.altitude.isValid()?gps.altitude.meters():0.0; d["satellites"]=gps.satellites.isValid()?gps.satellites.value():0; d["gnssAgeMs"]=gps.location.isValid()?gps.location.age():0;
  JsonObject present=d.createNestedObject("present");present["lux"]=hasLux;present["environment"]=hasBme;present["imu"]=hasImu;present["ppg"]=hasPpg;present["microphone"]=hasMic;present["gnss"]=gps.charsProcessed()>0;
  String out;serializeJson(d,out);Serial.println(out);ws.broadcastTXT(out);
}
