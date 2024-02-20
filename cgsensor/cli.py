"""
Raspberry Pi 拡張基板用センサー制御コマンドラインツール
Indoor Corgi, https://www.indoorcorgielec.com
GitHub: https://github.com/IndoorCorgi/cgsensor
Version 1.1

必要環境:
1) Raspberry Pi OS, Python3
2) I2Cインターフェース
  Raspberry PiでI2Cを有効にして下さい
  https://www.indoorcorgielec.com/resources/raspberry-pi/raspberry-pi-i2c/

Usage:
  cgsensor all [-v] [-f <filename>] [-c <interval>]
  cgsensor bme280 [-a]
  cgsensor tsl2572 [-v]
  cgsensor scd41 [-v]
  cgsensor scd41 start [--lp]
  cgsensor scd41 stop
  cgsensor scd41 read [-v]
  cgsensor scd41 config [--asc <on|off>] [--alt <altitude>] [--toff <offset>] [-p]
  cgsensor scd41 set-press <pressure>
  cgsensor scd41 frc [<target>]
  cgsensor scd41 factory
  cgsensor -h --help

Options:
  ------- 全センサー一括制御用コマンド -------
  all           接続されている全センサーの値を読み出して表示する. SCD41は必要に応じてstart(測定開始)する. 
                -vオプションで追加の測定値(SCD41の温度と湿度)を表示する. 
                -cオプションで約<interval>秒おきに継続して読み出して表示. 
                <interval>を省略した場合は60秒おき. SCD41がある場合は最短5秒程度必要. 
  -f <filename> 指定したファイルに時刻と測定結果を書き込む. 既に存在するファイルの場合は追記する. 
                追記する場合は列がずれないように, 同じセンサーの組み合わせと, 同じオプションの指定にする. 


  ------- BME280温湿度, 気圧センサー制御用コマンド -------
  bme280        1回のみの測定. デフォルトでI2Cアドレス0x76, -aオプションを指定すると0x77のセンサーを選択. 
  

  ------- TSL2572照度, 明るさセンサー制御用コマンド -------
  tsl2572       1回のみの測定. -vオプションで測定条件とADCレジスターの値を表示. 
  

  ------- SCD41二酸化炭素センサー制御用コマンド -------
  scd41         1回のみの測定. -vオプションで温度と湿度も表示. 定期測定中の場合は終了する. 
                measure_single_shotコマンドを使用するので, SCD40では動作しない.

  scd41 start   定期測定を開始. 5秒おきにセンサーで自動的に測定を行う. readで結果を取得する. 
                定期測定中はstop, read, set-press以外のコマンドは受け付けない. 
                single, frc, factoryを実行すると定期測定は終了する. 
                --lpオプションで30秒おきの省電力モードの定期測定にする. 

  scd41 stop    定期測定を終了.  

  scd41 read    定期測定の結果を読み出して表示. 最新の結果が無い場合は出力されるまで待つ. 
                -vオプションで温度と湿度も表示. 
                -cオプションで<interval>秒おきに継続して読み出して表示. 
                <interval>を省略した場合は次の結果が取得できたらすぐに読み出す. 

  scd41 config     センサーのコンフィグ情報を表示. -pオプションを指定するとEEPROMに現在の設定値
                   が保存され, 電源OFF後も保持される. 
  --asc <on|off>   自動キャリブレーションをON, OFFに変更する. 自動キャリブレーションの利用には, 
                   定期的に測定し, 最低週1回外気(400-450ppm)相当の環境が必要. 
                   400ppmを下回る環境で使用する場合はOFFにする必要がある. 
                   デフォルトON. 
  --alt <altitude> 測定値補正用の標高[m]を変更する. デフォルト0.  
  --toff <offset>  測定値補正用の温度オフセット値[°C]を変更する. (発熱に対処するため) CO2測定には影響しない. 
                   センサーの値からオフセット値を引いた値を出力する.  デフォルト4.0. 
  -p               設定をセンサーのEEPROMに保存し, 電源を落としても保持されるようにする. 

  scd41 set-press 測定値の補正に使用する気圧情報を設定する.
  <pressure>      周囲の気圧[hPa]

  scd41 frc     手動リキャリブレーション(FRC)を行う. <target>で現在の環境のCO2濃度[ppm]を指定する. 
                CO2濃度が不明な場合は新鮮な外気で実行する. 
                実施前にstartコマンドで3分以上CO2測定を行っておく必要がある. 
  <target>      現在の環境のCO2濃度[ppm]. 省略した場合は450ppm. 

  scd41 factory 工場出荷時設定にリセットする.
  
  -h --help     ヘルプを表示
"""

import os
import csv
from datetime import datetime
from docopt import docopt
from .bme280 import *
from .tsl2572 import *
from .scd41 import *


def cli():
  """
  コマンドラインツールを実行
  """
  args = docopt(__doc__)

  # I2Cバスを確認
  try:
    smbus2.SMBus(1)
  except FileNotFoundError:
    print('I2Cバスが開けませんでした. I2Cが有効になっているか確認して下さい. ')
    return

  #----------------------------
  # 全センサー
  if args['all']:
    # センサー制御クラス
    bme280list = [BME280(0x76), BME280(0x77)]
    tsl2572 = TSL2572()
    scd41 = SCD41()

    first_line = True

    try:
      while True:
        # ログ用の値を保存するリスト
        log_header = ['時刻']
        log_data = [datetime.now().strftime("%Y/%m/%d %H:%M:%S")]

        # BME280センサーを検出したら測定する
        for bme280 in bme280list:
          try:
            if bme280.forced():
              if bme280.i2c_addr == 0x77:
                sensor_title = 'BME280#2'
              else:
                sensor_title = 'BME280'

              if not args['-c']:
                print('{}'.format(sensor_title))
                print('  温度[°C]:  {}'.format(bme280.temperature))
                print('  湿度[%]:   {}'.format(bme280.humidity))
                print('  気圧[hPa]: {}'.format(bme280.pressure))
              log_header.extend([sensor_title + ' 温度[°C]', sensor_title + ' 湿度[%]', sensor_title + ' 気圧[hPa]'])
              log_data.extend([bme280.temperature, bme280.humidity, bme280.pressure])
          except IOError:
            continue

        # TSL2572センサーを検出したら測定する
        try:
          if tsl2572.single_auto_measure():
            if not args['-c']:
              print('TSL2572')
              print('  明るさ[lux]:  {}'.format(tsl2572.illuminance))
            log_header.append('TSL2572 明るさ[lux]')
            log_data.append(tsl2572.illuminance)
        except IOError:
          pass

        # SCD41センサーを検出したら測定する
        try:
          result = scd41.read_measurement()

          # 測定値が読み出せなかった場合はstartコマンドを使う
          if not result:
            scd41.stop_periodic_measurement()
            scd41.start_periodic_measurement()
            result = scd41.read_measurement(timeout=6)

          # 測定結果が読み出せた場合
          if result:
            if not args['-c']:
              print('SCD41')
              print('  CO2濃度[ppm]: {}'.format(scd41.co2))
            log_header.append('SCD41 CO2濃度[ppm]')
            log_data.append(scd41.co2)
            if args['-v']:
              if not args['-c']:
                print('  温度[°C]: {}'.format(scd41.temperature))
                print('  湿度[%]: {}'.format(scd41.humidity))
              log_header.extend(['SCD41 温度[°C]', 'SCD41 湿度[%]'])
              log_data.extend([scd41.temperature, scd41.humidity])
        except IOError:
          pass

        # センサーが1つも見つからなかった場合
        if 1 == len(log_header):
          print('センサーが見つかりませんでした. ')
          return

        # ファイルに記録
        if None != args['-f']:
          log_exists = os.path.isfile(args['-f'])  # ファイルが既にあるか確認
          if os.path.dirname(args['-f']) != '':
            os.makedirs(os.path.dirname(args['-f']), exist_ok=True)  # 必要に応じてディレクトリ作成
          with open(args['-f'], 'a') as f:
            writer = csv.writer(f)
            if not log_exists:
              writer.writerow(log_header)
            writer.writerow(log_data)
            if not args['-c']:
              print('ファイル{}に書き込みました. '.format(args['-f']))

        # 継続するかどうか
        if args['-c']:
          if first_line:
            print(', '.join(log_header))
            first_line = False

          print(', '.join(map(str, log_data)))
          if args['<interval>'] != None:
            if not check_digit('<interval>', args['<interval>'], 1, 10000):
              return
            time.sleep(int(args['<interval>']))
          else:
            time.sleep(60)
        else:
          return
    except KeyboardInterrupt:
      return

  #----------------------------
  # BME280
  elif args['bme280']:
    if args['-a']:
      bme280 = BME280(0x77)
      sensor_name = 'BME280#2'
    else:
      bme280 = BME280(0x76)
      sensor_name = 'BME280'

    try:
      if not bme280.forced():
        print(sensor_name + ' 測定に失敗しました. ')
        return
      print(sensor_name + ' 測定')
      print('  温度[°C]:  {}'.format(bme280.temperature))
      print('  湿度[%]:   {}'.format(bme280.humidity))
      print('  気圧[hPa]: {}'.format(bme280.pressure))
    except IOError:
      print(sensor_name + ' センサーとの通信に失敗しました. ')

  #----------------------------
  # TSL2572
  if args['tsl2572']:
    tsl2572 = TSL2572()

    try:
      if not tsl2572.single_auto_measure():
        print('TSL2572 測定に失敗しました. ')
        return
      print('TSL2572 測定')
      print('  明るさ[lux]:  {}'.format(tsl2572.illuminance))

      if args['-v']:
        print('  測定倍率: ', end='')
        if tsl2572.AGAIN_016 == tsl2572.again:
          print('0.16')
        elif tsl2572.AGAIN_1 == tsl2572.again:
          print('1')
        elif tsl2572.AGAIN_8 == tsl2572.again:
          print('8')
        elif tsl2572.AGAIN_16 == tsl2572.again:
          print('16')
        elif tsl2572.AGAIN_120 == tsl2572.again:
          print('120')
        print('  測定時間[ms]:  {}'.format(tsl2572.integ_cycles * 2.73))
        print('  ADC Ch0:  {}'.format(tsl2572.adc_ch0))
        print('  ADC Ch1:  {}'.format(tsl2572.adc_ch1))
    except IOError:
      print('TSL2572 センサーとの通信に失敗しました. ')

  #----------------------------
  # SCD41
  if args['scd41']:
    scd41 = SCD41()
    try:
      if args['start']:
        if args['--lp']:
          scd41.start_low_power_periodic_measurement()
          print('SCD41 定期測定(省電力30秒おき)を開始しました. ')
        else:
          scd41.start_periodic_measurement()
          print('SCD41 定期測定(5秒おき)を開始しました. ')

      elif args['stop']:
        scd41.stop_periodic_measurement()
        print('SCD41 定期測定を停止しました. ')

      elif args['read']:
        if not scd41.read_measurement(timeout=35):
          print('SCD41 測定結果の読み出しに失敗しました. ')
          return

        print('SCD41 測定結果の読み出し')
        print('  CO2濃度[ppm]: {}'.format(scd41.co2))
        if args['-v']:
          print('  温度[°C]: {}'.format(scd41.temperature))
          print('  湿度[%]: {}'.format(scd41.humidity))

      elif args['config']:
        # ASC変更
        if args['--asc'] != None:
          if args['--asc'] == 'on':
            scd41.set_automatic_self_calibration_enabled(True)
            print('SCD41 自動キャリブレーション(ASC)を有効にしました. ')
          elif args['--asc'] == 'off':
            scd41.set_automatic_self_calibration_enabled(False)
            print('SCD41 自動キャリブレーション(ASC)を無効にしました. ')
          else:
            print('--ascで指定した値{}が正しくありません. onかoffを指定して下さい. '.format(args['--asc']))
            return

        # 標高情報変更
        if args['--alt'] != None:
          if not check_digit('--alt', args['--alt'], 0, 5000):
            return

          scd41.set_sensor_altitude(int(args['--alt']))
          print('SCD41 標高設定を{}[m]に変更しました. '.format(args['--alt']))

        # 温度オフセット情報変更
        if args['--toff'] != None:
          if not check_float('--toff', args['--toff'], 0.0, 100.0):
            return

          scd41.set_temperature_offset(float(args['--toff']))
          print('SCD41 温度オフセットを{}[°C]に変更しました. '.format(args['--toff']))

        # コンフィグ情報読み出し, 表示
        val = scd41.get_serial_number()
        print('SCD41 コンフィグ情報')
        print('  シリアル番号: 0x{:X}'.format(val))

        val = scd41.get_automatic_self_calibration_enabled()
        print('  自動キャリブレーション(ASC): ', end='')
        if val:
          print('有効')
        else:
          print('無効')

        val = scd41.get_sensor_altitude()
        print('  標高設定[m]: {}'.format(val))

        val = scd41.get_temperature_offset()
        print('  温度オフセット[°C]: {}'.format(val))

        # EEPROMに設定値を保存
        if args['-p']:
          scd41.persist_settings()
          print('SCD41 EEPROMにコンフィグ情報を保存しました. ')

      elif args['set-press']:
        if not check_digit('<pressure>', args['<pressure>'], 800, 1200):
          return
        scd41.set_ambient_pressure(int(args['<pressure>']))
        print('SCD41 気圧情報を{}[hPa]に設定しました. '.format(args['<pressure>']))

      elif args['frc']:
        if args['<target>']:
          if not check_digit('<target>', args['<target>'], 0, 10000):
            return
          target = int(args['<target>'])
        else:
          target = 450

        if scd41.perform_forced_recalibration(target):
          print('SCD41 {}[ppm]を基準に手動リキャリブレーション(FRC)を実行しました. '.format(target))
        else:
          print('SCD41 手動リキャリブレーション(FRC)に失敗しました. ')

      elif args['factory']:
        if ask('SCD41 工場出荷時にリセットしてよろしいですか？'):
          scd41.stop_periodic_measurement()
          scd41.perform_factory_reset()
          print('SCD41 工場出荷時設定にリセットしました. ')

      # サブコマンドなしの場合は1回のみの測定
      else:
        scd41.stop_periodic_measurement()  # 定期測定は停止
        if not scd41.measure_single_shot():
          print('SCD41 測定に失敗しました. ')
        else:
          print('SCD41 測定')
          print('  CO2濃度[ppm]: {}'.format(scd41.co2))
          if args['-v']:
            print('  温度[°C]:     {}'.format(scd41.temperature))
            print('  湿度[%]:      {}'.format(scd41.humidity))
    except IOError:
      print('SCD41 センサーとの通信に失敗しました. 定期測定中は一部のコマンドは使用できません. ')


def check_digit(option, num, min, max):
  """
  文字列numがmin-maxの範囲の整数であればTrueを返す

  Args:
    option: エラーメッセージ用にオプションを指定する.
    num (str): 数値を表す文字列. 
    min: 許容最小値
    max: 許容最大値
  """
  val = False

  try:
    num_int = int(num)
    if num_int >= min and num_int <= max:
      val = True
  except ValueError:
    pass

  if not val and len(option) > 0:
    print('{} で指定した値 {} が正しくありません. {} - {} の範囲の数値を指定してください. '.format(option, num, min, max))
  return val


def check_float(option, num, min, max):
  """
  文字列numがmin-maxの範囲の小数であればTrueを返す

  Args:
    option: エラーメッセージ用にオプションを指定する.
    num (str): 数値を表す文字列. 
    min: 許容最小値
    max: 許容最大値
  """
  val = False

  try:
    num_int = float(num)
    if num_int >= min and num_int <= max:
      val = True
  except ValueError:
    pass

  if not val and len(option) > 0:
    print('{} で指定した値 {} が正しくありません. {} - {} の範囲の数値を指定してください. '.format(option, num, min, max))
  return val


def check_digit_list(option, num, val_list):
  """
  文字列numがval_listに含まれる数値であればTrueを返す

  Args:
    option: エラーメッセージ用にオプションを指定する.
    num (str): 数値を表す文字列. 
    val_list (list): 許容数値のリスト
  """
  val = False
  try:
    num_int = int(num)
    if num_int in val_list:
      val = True
  except ValueError:
    pass

  if not val and len(option) > 0:
    print('{} で指定した値 {} が正しくありません. {} のいずれかの数値を指定してください. '.format(option, num, val_list))
  return val


def ask(message, default=False):
  """
  Yes/No選択メッセージを表示してユーザーの入力を待つ. YesでTrue, NoでFalseを返す
  """
  if (default):
    add_str = ' [Y/n]: '
  else:
    add_str = ' [y/N]: '

  while True:
    choice = input(message + add_str).lower()
    if choice in ['y', 'yes']:
      return True
    elif choice in ['n', 'no']:
      return False
    elif choice in ['']:
      return default
