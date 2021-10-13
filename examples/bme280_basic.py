#!/usr/bin/env python3
"""
BME280センサー用サンプルコード
測定を行い、結果を読み出して表示する. 
Indoor Corgi, https://www.indoorcorgielec.com
GitHub: https://github.com/IndoorCorgi/cgsensor

必要環境:
1) Raspberry Pi OS, Python3
2) I2Cインターフェース
  Raspberry PiでI2Cを有効にして下さい
  https://www.indoorcorgielec.com/resources/raspberry-pi/raspberry-pi-i2c/

3) 拡張基板
  RPZ-IR-Sensor: https://www.indoorcorgielec.com/products/rpz-ir-sensor/
  RPi TPH Monitor: https://www.indoorcorgielec.com/products/rpi-tph-monitor-rev2/
  RPZ-CO2-Sensor: https://www.indoorcorgielec.com/products/rpz-co2-sensor/

4) cgsensorパッケージ
  sudo python3 -m pip install -U cgsensor
"""

import cgsensor  # インポート

bme280 = cgsensor.BME280(i2c_addr=0x76)  # BME280制御クラスのインスタンス, i2c_addrは0x76/0x77から選択

bme280.forced()  # Forcedモードで測定を行い, 結果をtemperature, pressure, humidityに入れる
print('気温 {}°C'.format(bme280.temperature))  # 気温を取得して表示
print('湿度 {}%'.format(bme280.humidity))  # 湿度を取得して表示
print('気圧 {}hPa'.format(bme280.pressure))  # 気圧を取得して表示
