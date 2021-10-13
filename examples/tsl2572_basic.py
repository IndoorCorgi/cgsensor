#!/usr/bin/env python3
"""
TSL2572センサー用サンプルコード
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

4) cgsensorパッケージ
  sudo python3 -m pip install -U cgsensor
"""

import cgsensor  # インポート

tsl2572 = cgsensor.TSL2572()  # TSL2572制御クラスのインスタンス

tsl2572.single_auto_measure()  # 条件を自動で調整しながら1回測定を行い, luxに結果を入れる
print('明るさ {}lux'.format(tsl2572.illuminance))  # 明るさを取得して表示
