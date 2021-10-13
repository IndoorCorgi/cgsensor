"""
Raspberry Pi用 照度, 明るさセンサーTSL2572制御モジュール
Indoor Corgi, https://www.indoorcorgielec.com
GitHub: https://github.com/IndoorCorgi/cgsensor
"""

import time
import smbus2


class TSL2572:
  """
  Raspberry Pi用 照度, 明るさセンサーTSL2572制御クラス

  Attributes:
    adc_ch0: ADCレジスターの読み出し値(Ch0)
    adc_ch1: ADCレジスターの読み出し値(Ch1)
    adc_humidity: ADCレジスターの読み出し値(湿度)
    again: 測定の倍率(ゲイン). AGAIN_xで指定. 
    integ_cycles: 測定の時間を決めるサイクル数. 1-256の整数. 
    illuminance: 計算後の照度(明るさ)の値[lux]
  """
  # 測定の倍率(ゲイン)
  AGAIN_016 = 0  # 0.16倍
  AGAIN_1 = 1  # 1倍
  AGAIN_8 = 2  # 8倍
  AGAIN_16 = 3  # 16倍
  AGAIN_120 = 4  # 120倍

  def __init__(self):
    self.i2c_addr = 0x39
    self.bus = smbus2.SMBus(1)
    self.adc_ch0 = 0
    self.adc_ch1 = 0
    self.illuminance = 0
    self.again = self.AGAIN_1
    self.integ_cycles = 1

  def read_register(self, addr, length):
    """
    I2Cでセンサーの指定アドレスからデータを読み出す
    
    Args:
      addr : 読み出しアドレス 8bit
      length : 読み出しデータの長さ. バイト数.

    Returns:
      list: 読み出しデータのリスト
    """
    addr = addr | 0xA0
    return self.bus.read_i2c_block_data(self.i2c_addr, addr, length)

  def write_register(self, addr, data):
    """
    I2Cでセンサーの指定アドレスにデータを書き込む

    Args:
      addr: 書き込みアドレス. 8bit. 
      data(list): 書き込みデータのリスト. [1バイト目, 2バイト目, ...]
    """
    addr = addr | 0xA0
    self.bus.write_i2c_block_data(self.i2c_addr, addr, data)

  def check_id(self):
    """
    センサーからIDを読み出して期待値と一致するか確認
    
    Returns:
      bool: 成功でTrue, 失敗でFalse
    """
    data = self.read_register(0x12, 1)

    # 3.3V TSL25721は0x34, 1.8V TSL25723は0x3D
    if (data[0] == 0x34) or (data[0] == 0x3D):
      return True
    return False

  def write_enable(self, pon=False, aen=False, wen=False):
    """
    Enableレジスターに書き込む. 機能の有効, 無効を切り替える.

    Args:
      pon (bool): TrueでPower ON
      aen (bool): Trueで定期的に測定開始
      wen (bool): Trueで測定間に待機時間を入れる
    """
    data = 0
    if pon:
      data |= 0x1

    if aen:
      data |= 0x2

    if wen:
      data |= 0x8

    self.write_register(0x0, [data])

  def write_atime(self, integ_cycles):
    """
    ALS integration time (測定時間)を書き込む

    Args:
      integ_cycles (int): 1-256の整数. atime = integ_cycles x 2.73[ms]
    
    Raises:
      VallueError: integ_cyclesが整数でないか, 範囲外
    """
    # 整数でない
    if not isinstance(integ_cycles, int):
      raise ValueError(integ_cycles)

    # 範囲外
    if integ_cycles < 1 or integ_cycles > 256:
      raise ValueError(integ_cycles)

    self.write_register(0x1, [256 - integ_cycles])

  def write_again(self, again):
    """
    ALS integration gain (倍率)を書き込む

    Args:
      again (int): AGAIN_xで指定
    """
    if self.AGAIN_016 == again:
      self.write_register(0xD, [0x4])
      self.write_register(0xF, [0])
    elif self.AGAIN_1 == again:
      self.write_register(0xD, [0])
      self.write_register(0xF, [0])
    elif self.AGAIN_8 == again:
      self.write_register(0xD, [0])
      self.write_register(0xF, [0x1])
    elif self.AGAIN_16 == again:
      self.write_register(0xD, [0])
      self.write_register(0xF, [0x2])
    elif self.AGAIN_120 == again:
      self.write_register(0xD, [0])
      self.write_register(0xF, [0x3])

  def read_status(self):
    """
    ステータスレジスターの値を読み出す

    Returns:
      int: AVALID bit. 1で測定結果あり. 0で測定結果なし.
      int: AINT bit. 1で割り込み発生. 0で割り込みなし.
    """
    data = self.read_register(0x13, 1)
    avalid = data[0] & 0x1
    aint = (data[0] & 0x10) >> 4
    return avalid, aint

  def read_adc(self):
    """
    ADCレジスターの値を読み出してadc_ch0, adc_ch1に入れる
    """
    data = self.read_register(0x14, 4)
    self.adc_ch0 = (data[1] << 8) | data[0]
    self.adc_ch1 = (data[3] << 8) | data[2]

  def single_als_integration(self):
    """
    integ_cycles, againの設定で1回測定を行い, adc_ch0, adc_ch1にADCレジスターの値を入れる. 
    """
    self.write_enable(pon=True, aen=False)  # 一度測定を停止
    self.write_atime(self.integ_cycles)
    self.write_again(self.again)
    self.write_enable(pon=True, aen=True)  # 測定開始

    # 結果を待つ
    while True:
      avalid, aint = self.read_status()
      if avalid == 1 and aint == 1:
        self.write_enable(pon=False, aen=False)  # 測定を停止
        break
      else:
        time.sleep(0.01)

    self.read_adc()

  def calculate_lux(self):
    """
    adc_ch0, adc_ch1, integ_cycles, againから照度(明るさ)を計算し, illuminanceに入れる. 
    """
    t = self.integ_cycles * 2.73

    if self.AGAIN_016 == self.again:
      g = 0.16
    elif self.AGAIN_1 == self.again:
      g = 1
    elif self.AGAIN_8 == self.again:
      g = 8
    elif self.AGAIN_16 == self.again:
      g = 16
    elif self.AGAIN_120 == self.again:
      g = 120

    cpl = (t * g) / 60
    lux1 = (self.adc_ch0 - 1.87 * self.adc_ch1) / cpl
    lux2 = (0.63 * self.adc_ch0 - self.adc_ch1) / cpl

    self.illuminance = round(max([0, lux1, lux2]), 1)

  def single_auto_measure(self):
    """
    条件を自動で調整しながら1回測定を行い, luxに結果を入れる

    Returns:
      bool: 成功でTrue, IDチェック失敗でFalse
    """
    if not self.check_id():
      return False

    # 1度短い時間で測定する
    self.integ_cycles = 4
    self.again = self.AGAIN_1
    self.single_als_integration()
    adc_max = max([self.adc_ch0, self.adc_ch1])
    margin = 0.8  # 判定マージン用倍率. ADCレジスターの上限 x margin以上に達したら条件を変える.

    # 1度目の結果をもとにinteg_cyclesとagainを決める
    if adc_max < 8.53 * margin:
      self.integ_cycles = 256
      self.again = self.AGAIN_120
    elif adc_max < 128 * margin:
      self.integ_cycles = 128
      self.again = self.AGAIN_16
    elif adc_max < 512 * margin:
      self.integ_cycles = 64
      self.again = self.AGAIN_8
    elif adc_max < 4096 * margin:
      self.integ_cycles = 64
      self.again = self.AGAIN_1
    else:
      self.integ_cycles = 64
      self.again = self.AGAIN_016

    # 本番の測定
    self.single_als_integration()
    self.calculate_lux()

    return True
