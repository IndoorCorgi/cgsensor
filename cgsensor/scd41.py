"""
Raspberry Pi用 CO2(二酸化炭素)センサーSCD41制御モジュール
Indoor Corgi, https://www.indoorcorgielec.com
GitHub: https://github.com/IndoorCorgi/cgsensor
"""

import time
import smbus2


class SCD41:
  """
  Raspberry Pi用 CO2(二酸化炭素)センサーSCD41制御クラス

  Attributes:
    co2: 測定値(CO2[ppm])
    temperature: 測定値(温度[°C])
    humidity: 測定値(湿度[%])
  """

  def __init__(self):
    self.bus = smbus2.SMBus(1)
    self.i2c_addr = 0x62

    self.co2 = 0
    self.temperature = 0
    self.humidity = 0

  def read_register(self, addr, length):
    """
    I2Cでセンサーの指定アドレスからデータを読み出す

    Args:
      addr: 読み出しアドレス. 16bit. 
      length: 読み出しデータの長さ. バイト数.
    
    Returns:
      list: 読み出しデータのリスト
    """
    msg_write = smbus2.i2c_msg.write(self.i2c_addr, [addr >> 8, addr & 0xFF])
    msg_read = smbus2.i2c_msg.read(self.i2c_addr, length)
    self.bus.i2c_rdwr(msg_write, msg_read)
    return list(msg_read)

  def write_register(self, addr, data=None):
    """
    I2Cでセンサーの指定アドレスにデータを書き込む

    Args:
      addr: 書き込みアドレス. 8bit. 
      data(list): 書き込みデータのリスト. 省略したらアドレスのみ書き込む(コマンド).
    
    Returns:
      int: 読み出した16bitのデータ
    """
    write_data = [addr >> 8, addr & 0xFF]
    if data != None:
      for b in data:
        write_data.append(b)
      write_data.append(self.calculate_crc(data))

    msg_write = smbus2.i2c_msg.write(self.i2c_addr, write_data)
    self.bus.i2c_rdwr(msg_write)

  def calculate_crc(self, data):
    """
    CRCを計算
    
    Args:
      data: CRCを計算するデータのリスト. [1バイト目, 2バイト目]. 
    
    Returns:
      int: CRC計算結果
    """
    crc = 0xFF
    for i in range(len(data)):
      crc ^= data[i]
      for j in range(8):
        if (crc & 0x80) == 0:
          crc = (crc << 1) & 0xFF
        else:
          crc = ((crc << 1) ^ 0x31) & 0xFF

    return crc

  def start_periodic_measurement(self):
    """
    5秒おきの定期測定を開始. 測定中は使用できるコマンドが以下に制限される. データシート参照.
    - read_measurement
    - stop_periodic_measurement
    - set_ambient_pressure
    - get_data_ready_status
    """
    self.write_register(0x21b1)

  def start_low_power_periodic_measurement(self):
    """
    30秒おきの定期測定を開始. 測定中は使用できるコマンドが以下に制限される. データシート参照.
    - read_measurement
    - stop_periodic_measurement
    - set_ambient_pressure
    - get_data_ready_status
    """
    self.write_register(0x21ac)

  def measure_single_shot(self, timeout=10):
    """
    単発の測定を開始. 測定完了まで5秒かかる. 電源投入後は, 正確な測定のため, 3回以上の測定が推奨.
    
    Args:
      timeout: 新しい測定データを待つ秒数. 0だと待たずに処理を返す.
    
    Returns:
      bool: 成功でTrue, タイムアウトでFalse. Trueの場合はco2, temperature, humidityの値が更新される
    """
    self.write_register(0x219d)
    return self.read_measurement(timeout)

  def stop_periodic_measurement(self, wait=True):
    """
    定期測定を終了
    
    Args:
      wait: Trueなら停止までの500ms以上待機する. Falseならすぐに処理を返す.
    """
    self.write_register(0x3f86)
    if wait:
      time.sleep(0.6)

  def get_data_ready_status(self):
    """
    新しい測定データがあるか確認
    
    Returns:
      bool: 新しいデータがあればTrue, 無ければFalse
    
    Raises:
      CRCMismatchError: CRCが一致しない
    """
    data = self.read_register(0xe4b8, 3)

    # CRC確認
    if self.calculate_crc([data[0], data[1]]) != data[2]:
      raise CRCMismatchError

    if (data[1] & 0x3) == 0:
      return False
    return True

  def read_measurement(self, timeout=0):
    """
    測定データを読み出す. 成功した場合はco2, temperature, humidityの値が更新される

    Args:
      timeout: 新しい測定データを待つ秒数. 0だと待たずに処理を返す.
    
    Returns:
      bool: 成功でTrue, タイムアウトでFalse
    
    Raises:
      ValueError: タイムアウトの値が範囲外
      CRCMismatchError: CRCが一致しない
    """
    if int(timeout) < 0:
      raise ValueError(timeout)

    # 100msおきに測定データがあるかチェック
    for i in range((timeout * 10) + 1):
      ready = self.get_data_ready_status()

      # 新しいデータがある
      if ready:
        break

      # タイムアウト
      if i >= timeout * 10:
        return False

      time.sleep(0.1)  # 待機

    # 測定データ読み出し
    data = self.read_register(0xec05, 9)

    # CRC確認
    for i in range(3):
      if self.calculate_crc([data[i * 3], data[i * 3 + 1]]) != data[i * 3 + 2]:
        raise CRCMismatchError

    self.co2 = (data[0] << 8) + data[1]
    self.temperature = round(-45 + 175 * ((data[3] << 8) + data[4]) / (2**16), 1)
    self.humidity = round(100 * ((data[6] << 8) + data[7]) / (2**16), 1)

    return True

  def set_temperature_offset(self, offset):
    """
    測定値補正用の温度オフセット値を書き込む. 
    温度測定の際にオフセット値が引かれる. 実際の使用環境の発熱を考慮して決める. デフォルトは4.
    電源立ち下げ後も設定を保存するにはpersist_settingsコマンドを実行する必要がある.

    Args:
      offset (float): オフセット[°C]の値
    """
    offset_w = round(offset * (2**16) / 175)
    if offset_w > 0xFFFF:  # オフセット値が範囲外
      raise ValueError(offset)
    self.write_register(0x241d, [offset_w >> 8, offset_w & 0xFF])

  def get_temperature_offset(self):
    """
    測定値補正用の温度オフセット値を読み出す

    Returns:
      float: 設定されているオフセット値を[°C]単位に直したもの
    
    Raises:
      CRCMismatchError: CRCが一致しない
    """
    data = self.read_register(0x2318, 3)

    # CRC確認
    if self.calculate_crc([data[0], data[1]]) != data[2]:
      raise CRCMismatchError

    else:
      return round(175 * ((data[0] << 8) + data[1]) / (2**16), 1)

  def set_sensor_altitude(self, altitude):
    """
    測定値補正用の標高情報を書き込む. 
    電源立ち下げ後も設定を保存するにはpersist_settingsコマンドを実行する必要がある.

    Args:
      altitude (int): 標高[m]の値
    """
    self.write_register(0x2427, [altitude >> 8, altitude & 0xFF])

  def get_sensor_altitude(self):
    """
    測定値補正用の標高情報を読み出す

    Returns:
      int: 設定されている標高情報[m]
    
    Raises:
      CRCMismatchError: CRCが一致しない
    """
    data = self.read_register(0x2322, 3)

    # CRC確認
    if self.calculate_crc([data[0], data[1]]) != data[2]:
      raise CRCMismatchError

    return (data[0] << 8) + data[1]

  def set_ambient_pressure(self, pressure):
    """
    測定値補正用の気圧情報を書き込む

    Args:
      pressure: 気圧[hPa]の値
    """
    self.write_register(0xe000, [pressure >> 8, pressure & 0xFF])

  def perform_forced_recalibration(self, target=400):
    """
    手動キャリブレーション(FRC)
    実施前に3分程度のCO2測定を行った後, 定期測定は停止しておく必要がある. データシート参照.

    Args:
      target: 既知のCO2濃度[ppm]. 外気で行う場合は400.
    
    Returns:
      bool: 成功ならTrue. 失敗ならFalse.
    """
    self.write_register(0x362f, [target >> 8, target & 0xFF])
    time.sleep(0.5)  # 400ms以上待機

    data = self.read_register(0x362f, 3)

    if (data[0] == 0xff) and (data[1] == 0xff):
      return False

    # キャリブレーションで、センサー内部のppm補正値を変化させた相対量が取得できる
    frc_correction = (data[0] << 8) + data[1] - 0x8000

    return True

  def set_automatic_self_calibration_enabled(self, enable=True):
    """
    自動キャリブレーション(ASC)を有効/無効化する. デフォルトは有効.
    電源立ち下げ後も設定を保存するにはpersist_settingsコマンドが必要.
    ASCを使う場合, 週1回以上の頻度で外気相当の400ppm環境が必要. データシート参照.

    Args:
      enable: 有効化するならTrue. 無効化するならFalse.
    """
    if enable:
      data = 1
    else:
      data = 0
    self.write_register(0x2416, [data >> 8, data & 0xff])

  def get_automatic_self_calibration_enabled(self):
    """
    自動キャリブレーション(ASC)状態を読み出す. 

    Returns:
      bool: 有効ならTrue. 無効ならFalse.
    """
    data = self.read_register(0x2313, 3)

    if (data[0] << 8) + data[1] == 1:
      return True
    else:
      return False

  def persist_settings(self, wait=True):
    """
    設定情報をEEPROMに保存して, 電源を落としても保存されるようにする
    
    Args:
      wait: Trueなら完了までの800ms以上待機する. Falseならすぐに処理を返す.
    """
    self.write_register(0x3615)
    if wait:
      time.sleep(0.9)

  def perform_factory_reset(self, wait=True):
    """
    工場出荷時の設定に戻す. 初期設定に戻り, EEPROMの設定, キャリブレーション情報も消去される.

    Args:
      wait: Trueなら完了までの1200ms以上待機する. Falseならすぐに処理を返す.
    """
    self.write_register(0x3632)
    if wait:
      time.sleep(1.3)

  def reinit(self):
    """
    EEPROMの設定を読み出して反映させる.
    """
    self.write_register(0x3646)
    time.sleep(0.04)

  def get_serial_number(self):
    """
    シリアル番号を取得
    
    Returns:
      int: シリアル番号.

    Raises:
      CRCMismatchError: CRCが一致しない
    """
    data = self.read_register(0x3682, 9)

    # CRC確認
    for i in range(3):
      if self.calculate_crc([data[i * 3], data[i * 3 + 1]]) != data[i * 3 + 2]:
        raise CRCMismatchError

    return ((data[0] << 40) + (data[1] << 32) + (data[2] << 24) + (data[3] << 16) + (data[4] << 8) + data[5])


class CRCMismatchError(Exception):
  """
  センサーから読み出し時にCRCが一致しなかった例外クラス
  """
  pass