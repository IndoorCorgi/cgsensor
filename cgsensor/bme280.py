"""
Raspberry Pi用 温湿度気圧センサーBME280制御モジュール
Indoor Corgi, https://www.indoorcorgielec.com
GitHub: https://github.com/IndoorCorgi/cgsensor
"""

import time
import smbus2


class BME280:
  """
  Raspberry Pi用 温湿度気圧センサーBME280制御クラス

  Attributes:
    calibration_data (dict): センサーから読み出したキャリブレーション名, 値の辞書
    t_fine : キャリブレーション計算途中のパラメータ
    adc_temperature: ADCレジスターの読み出し値(温度)
    adc_pressure: ADCレジスターの読み出し値(気圧)
    adc_humidity: ADCレジスターの読み出し値(湿度)
    temperature: キャリブレーション計算後の値(温度[°C])
    pressure: キャリブレーション計算後の値(気圧[hPa])
    humidity: キャリブレーション計算後の値(湿度[%])
  """
  # モード
  MODE_SLEEP = 0
  MODE_FORCED = 1
  MODE_NORMAL = 3

  # オーバーサンプリング
  OVER_SAMPLING_1 = 1
  OVER_SAMPLING_2 = 2
  OVER_SAMPLING_4 = 3
  OVER_SAMPLING_8 = 4
  OVER_SAMPLING_16 = 5

  # 定期測定間隔 t_standby
  T_STANDBY_05MS = 0
  T_STANDBY_62MS = 1
  T_STANDBY_125MS = 2
  T_STANDBY_250MS = 3
  T_STANDBY_500MS = 4
  T_STANDBY_1000MS = 5
  T_STANDBY_10MS = 6
  T_STANDBY_20MS = 7

  # IIRフィルター
  FILTER_OFF = 0
  FILTER_2 = 1
  FILTER_4 = 2
  FILTER_8 = 3
  FILTER_16 = 4

  def __init__(self, i2c_addr=0x76):
    """
    Args:
      i2c_addr: センサーのI2Cアドレス. 7bit. 
    """
    self.i2c_addr = i2c_addr
    self.bus = smbus2.SMBus(1)

    self.calibration_data = {}
    self.t_fine = 0

    self.adc_temperature = 0
    self.adc_pressure = 0
    self.adc_humidity = 0

    self.temperature = 0
    self.pressure = 0
    self.humidity = 0

  def read_register(self, addr, length):
    """
    I2Cでセンサーの指定アドレスからデータを読み出す

    Args:
      addr: 読み出しアドレス. 8bit. 
      length: 読み出しデータの長さ. バイト数.
    
    Returns:
      list: 読み出しデータのリスト
    """
    return self.bus.read_i2c_block_data(self.i2c_addr, addr, length)

  def read_register_word(self, addr):
    """
    I2Cでセンサーの指定アドレスから16bitのデータを読み出す

    Args:
      addr: 読み出しアドレス. 8bit. 
      length: 読み出しデータの長さ. バイト数.
    
    Returns:
      int: 読み出した16bitのデータ
    """
    data = self.bus.read_i2c_block_data(self.i2c_addr, addr, 2)
    return data[0] + (data[1] << 8)

  def write_register(self, addr, data):
    """
    I2Cでセンサーの指定アドレスにデータを書き込む

    Args:
      addr: 書き込みアドレス. 8bit. 
      data(list): 書き込みデータのリスト. [1バイト目, 2バイト目, ...]
    """
    self.bus.write_i2c_block_data(self.i2c_addr, addr, data)

  def check_id(self):
    """
    センサーからIDを読み出して期待値と一致するか確認
    
    Returns:
      bool: 成功でTrue, 失敗でFalse
    """
    data = self.read_register(0xD0, 1)

    if data[0] == 0x60:
      return True
    return False

  def read_status(self):
    """
    ステータスレジスターの値を読み出す
    
    Returns:
      int: measuring bit. 1で測定中. 0で測定中ではない.
      int: im_update bit. 1で転送中. 0で転送中ではない.
    """
    data = self.read_register(0xF3, 1)
    measuring = (data[0] & 0x8) >> 3
    im_update = data[0] & 0x1
    return measuring, im_update

  def read_calibration_data(self):
    """
    センサーからキャリブレーションレジスターの値を読み出し, calibration_dataに入れる.
    """
    self.calibration_data['dig_T1'] = self.read_register_word(0x88)
    self.calibration_data['dig_T2'] = self._get_signed16(self.read_register_word(0x8A))
    self.calibration_data['dig_T3'] = self._get_signed16(self.read_register_word(0x8C))
    self.calibration_data['dig_P1'] = self.read_register_word(0x8E)
    self.calibration_data['dig_P2'] = self._get_signed16(self.read_register_word(0x90))
    self.calibration_data['dig_P3'] = self._get_signed16(self.read_register_word(0x92))
    self.calibration_data['dig_P4'] = self._get_signed16(self.read_register_word(0x94))
    self.calibration_data['dig_P5'] = self._get_signed16(self.read_register_word(0x96))
    self.calibration_data['dig_P6'] = self._get_signed16(self.read_register_word(0x98))
    self.calibration_data['dig_P7'] = self._get_signed16(self.read_register_word(0x9A))
    self.calibration_data['dig_P8'] = self._get_signed16(self.read_register_word(0x9C))
    self.calibration_data['dig_P9'] = self._get_signed16(self.read_register_word(0x9E))
    self.calibration_data['dig_H1'] = self.read_register(0xA1, 1)[0]
    self.calibration_data['dig_H2'] = self._get_signed16(self.read_register_word(0xE1))
    self.calibration_data['dig_H3'] = self.read_register(0xE3, 1)[0]
    self.calibration_data['dig_H4'] = self._get_signed16((self.read_register(0xE4, 1)[0] << 4) +
                                                         (self.read_register(0xE5, 1)[0] & 0xF))
    self.calibration_data['dig_H5'] = self._get_signed16(self.read_register_word(0xE5) >> 4)
    self.calibration_data['dig_H6'] = self._get_signed8(self.read_register(0xE7, 1)[0])

  def read_adc(self):
    """
    ADCレジスターの値を読み出してadc_temperature, adc_pressure, adc_humidityに入れる
    """
    data = self.read_register(0xF7, 8)

    self.adc_pressure = (data[0] << 12) + (data[1] << 4) + (data[2] >> 4)
    self.adc_temperature = (data[3] << 12) + (data[4] << 4) + (data[5] >> 4)
    self.adc_humidity = (data[6] << 8) + data[7]

  def write_config(self, t_standby=T_STANDBY_05MS, filter=FILTER_OFF):
    """
    コンフィグレジスター(config)にNormal mode測定間隔, フィルター設定を書き込む

    Args:
      t_standby: Normal mode測定間隔. T_STANDBY_xで指定. 
      filter: 温度のオーバーサンプリング. OVER_SAMPLING_xで指定.
    """
    data = (t_standby << 5) | (filter << 2)
    self.write_register(0xF5, [data])  # ctrl_configレジスター

  def write_ctrl(self,
                 mode=MODE_SLEEP,
                 os_temperature=OVER_SAMPLING_1,
                 os_pressure=OVER_SAMPLING_1,
                 os_humidity=OVER_SAMPLING_1):
    """
    コントロールレジスター(ctrl)にオーバーサンプリング設定, 測定モードを書き込む

    Args:
      mode: センサーモード. MODE_xで指定. FORCED, NORMALを書くと測定が始まる 
      os_temperature: 温度のオーバーサンプリング. OVER_SAMPLING_xで指定.
      os_pressure: 気圧のオーバーサンプリング. OVER_SAMPLING_xで指定.
      os_humidity: 湿度のオーバーサンプリング. OVER_SAMPLING_xで指定.
    """
    data = os_humidity
    self.write_register(0xF2, [data])  # ctrl_humレジスター

    data = (os_temperature << 5) | (os_pressure << 2) | mode
    self.write_register(0xF4, [data])  # ctrl_measレジスター

  def write_reset(self):
    """
    リセットレジスターに書き込んでソフトウェアリセットする
    """
    self.write_register(0xE0, [0xB6])  # resetレジスター

  def forced(self):
    """
    Forcedモードで測定を行い, 結果をtemperature, pressure, humidityに入れる
    
    Returns:
      bool: 成功でTrue, IDチェック失敗でFalse
    """
    # IDチェック
    if not self.check_id():
      return False

    self.write_config()
    self.write_ctrl(mode=self.MODE_FORCED,
                    os_temperature=self.OVER_SAMPLING_16,
                    os_pressure=self.OVER_SAMPLING_16,
                    os_humidity=self.OVER_SAMPLING_16)
    time.sleep(0.01)

    self.read_measured_values()
    return True

  def read_measured_values(self):
    """
    キャリブレーションデータとADCレジスターを読み出し, 結果をtemperature, pressure, humidityに入れる
    """
    # 測定中の場合は完了まで待機
    while True:
      measuring, im_update = self.read_status()
      if 0 == measuring:  # 測定完了
        break

      time.sleep(0.001)

    self.read_calibration_data()  # キャリブレーションデータ読み出し
    self.read_adc()  # ADCレジスター読み出し

    # キャリブレーション計算
    self.compensate_temperature()
    self.compensate_pressure()
    self.compensate_humidity()

  def compensate_temperature(self):
    """
    calibration_dataとadc_temperatureの値から気圧を計算し, temperatureに入れる
    有効な測定値が無い場合はtemperatureに0が入る
    """
    # 測定値なし
    if 0x80000 == self.adc_temperature:
      self.temperature = 0
      return

    var1 = ((((self.adc_temperature >> 3) - (self.calibration_data['dig_T1'] << 1))) *
            (self.calibration_data['dig_T2'])) >> 11
    var2 = (((((self.adc_temperature >> 4) - (self.calibration_data['dig_T1'])) *
              ((self.adc_temperature >> 4) - (self.calibration_data['dig_T1']))) >> 12) *
            (self.calibration_data['dig_T3'])) >> 14
    self.t_fine = var1 + var2
    self.temperature = round(((self.t_fine * 5 + 128) >> 8) / 100, 1)

  def compensate_pressure(self):
    """
    calibration_dataとadc_pressureの値から気圧を計算し, pressureに入れる
    compensate_temperatureで計算したt_fineの値を利用するので前もって実行が必要
    有効な測定値が無い場合はpressureに0が入る
    """
    # 測定値なし
    if 0x80000 == self.adc_pressure:
      self.pressure = 0
      return

    var1 = self.t_fine - 128000
    var2 = var1 * var1 * self.calibration_data['dig_P6']
    var2 = var2 + ((var1 * self.calibration_data['dig_P5']) << 17)
    var2 = var2 + (self.calibration_data['dig_P4'] << 35)
    var1 = ((var1 * var1 * self.calibration_data['dig_P3']) >> 8) + ((var1 * self.calibration_data['dig_P2']) << 12)
    var1 = (((1 << 47) + var1)) * (self.calibration_data['dig_P1']) >> 33
    if var1 == 0:
      return

    p = 1048576 - self.adc_pressure
    p = (((p << 31) - var2) * 3125) // var1
    var1 = (self.calibration_data['dig_P9'] * (p >> 13) * (p >> 13)) >> 25
    var2 = (self.calibration_data['dig_P8'] * p) >> 19
    p = ((p + var1 + var2) >> 8) + ((self.calibration_data['dig_P7']) << 4)
    self.pressure = round(p / 25600, 1)

  def compensate_humidity(self):
    """
    calibration_dataとadc_humidityの値から気圧を計算し, humidityに入れる
    compensate_temperatureで計算したt_fineの値を利用するので前もって実行が必要
    有効な測定値が無い場合はhumidityに0が入る
    """
    # 測定値なし
    if 0x8000 == self.adc_humidity:
      self.humidity = 0
      return

    v_x1_u32r = (self.t_fine - 76800)
    v_x1_u32r = (((((self.adc_humidity << 14) - ((self.calibration_data['dig_H4']) << 20) -
                    ((self.calibration_data['dig_H5']) * v_x1_u32r)) + 16384) >> 15) *
                 (((((((v_x1_u32r * self.calibration_data['dig_H6']) >> 10) *
                      (((v_x1_u32r * self.calibration_data['dig_H3']) >> 11) + 32768)) >> 10) + 2097152) *
                   self.calibration_data['dig_H2'] + 8192) >> 14))
    v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * self.calibration_data['dig_H1']) >> 4))
    if v_x1_u32r < 0:
      v_x1_u32r = 0
    if v_x1_u32r > 419430400:
      v_x1_u32r = 419430400
    self.humidity = round((v_x1_u32r >> 12) / 1024, 1)

  def _get_signed8(self, uint):
    """
    8bit unsigned intから8bit signed intを計算
    """
    if uint > 127:
      return uint - 256
    return uint

  def _get_signed16(self, uint):
    """
    16bit unsigned intから16bit signed intを計算
    """
    if uint > 32767:
      return uint - 65536
    return uint
