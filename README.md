## 概要
Indoor Corgi製Raspberry Pi用拡張基板の各種センサーを制御するソフトウェアです。
コマンドラインツールを使えば1行もコードを書かずに測定や記録ができるほか、Pythonパッケージでご自身のプログラムから簡単にセンサーを制御できます。

## 対応センサー
- BME280 温度/湿度/気圧センサー
- TSL2572 明るさ(照度)センサー
- SCD41 CO2(二酸化炭素)センサー

## 必要環境
ハードウェア: 40ピン端子を持つRaspberry Piシリーズ \
OS: Raspberry Pi OS

## 動作確認済モデル
- Raspberry Pi 4 Model B
- Raspberry Pi 3 Model B/B+
- Raspberry Pi Zero W/WH
- Raspberry Pi Zero

## 拡張基板
- [RPZ-IR-Sensor](https://www.indoorcorgielec.com/products/rpz-ir-sensor/) (Raspberry Pi用 温度/湿度/気圧/明るさ/赤外線 ホームIoT拡張ボード)
- [RPi TPH Monitor](https://www.indoorcorgielec.com/products/rpi-tph-monitor-rev2/) (Raspberry Pi用 温度/湿度/気圧/赤外線 ホームIoT拡張ボード)

## インストール
以下のコマンドでインストール/アップグレードできます。

`sudo python3 -m pip install -U cgsensor`

## 使い方
コマンドラインから`cgsensor -h`を実行することでオプションの解説が表示されます。各センサーの使い方は、以下の解説記事をご参照下さい。

- [BME280センサーとRaspberry Piで気温、湿度、気圧を測定する](https://www.indoorcorgielec.com/resources/raspberry-pi/cgsensor-bme280/)
