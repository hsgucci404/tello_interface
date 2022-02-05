#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from djitellopy import Tello    # DJITelloPyのTelloクラスをインポート
import time         # time.sleepを使いたいので
import cv2          # OpenCVを使うため
import numpy as np  # 四角形ポリゴンの描画のために必要

# メイン関数
def main():
    # 初期化部
    # Telloクラスを使って，tellというインスタンス(実体)を作る
    tello = Tello(retry_count=1)    # 応答が来ないときのリトライ回数は1(デフォルトは3)
    tello.RESPONSE_TIMEOUT = 0.01   # コマンド応答のタイムアウトは短くした(デフォルトは7)

    # Telloへ接続
    tello.connect()

    # 画像転送を有効にする
    tello.streamoff()   # 誤動作防止の為、最初にOFFする
    tello.streamon()    # 画像転送をONに
    frame_read = tello.get_frame_read()     # 画像フレームを取得するBackgroundFrameReadクラスのインスタンスを作る

    current_time = time.time()  # 現在時刻の保存変数
    pre_time = current_time     # 5秒ごとの'command'送信のための時刻変数

    motor_on = False                    # モータON/OFFのフラグ
    camera_dir = Tello.CAMERA_FORWARD   # 前方/下方カメラの方向のフラグ

    # OpenCV内臓のQRコードリーダーの準備
    qr = cv2.QRCodeDetector()

    pre_qr_msg = None	# 前回見えたQRコードのテキストを格納
    cnt_qr_msg = 0		# 同じテキストが見えた回数を記憶する変数
    cmds = None		# 認識したQRコードをTelloのコマンドとして使う
    cmd_len = 0     # コマンドの文字数
    cmd_index = 0	# 実行するコマンドの番号

    # 自動モードフラグ
    auto_mode = 0
    
    time.sleep(0.5)     # 通信が安定するまでちょっと待つ

    # ループ部
    # Ctrl+cが押されるまでループ
    try:
        # 永久ループで繰り返す
        while True:

            # (A) 画像取得
            image = frame_read.frame    # 映像を1フレーム取得しimage変数に格納

            # (B) 画像サイズ変更と、カメラ方向による回転
            small_image = cv2.resize(image, dsize=(480,360) )   # 画像サイズを半分に変更

            if camera_dir == Tello.CAMERA_DOWNWARD:     # 下向きカメラは画像の向きが90度ずれている
                small_image = cv2.rotate(small_image, cv2.ROTATE_90_CLOCKWISE)      # 90度回転して、画像の上を前方にする

            # (C) ここから画像処理
            # 自動制御フラグが0FF(=0)のときには，QRコード認識処理を行う
            if auto_mode == 0:
                # QRコードの検出とデコード処理
                qr_msg, qr_points, qr_option = qr.detectAndDecode( small_image )
                print(qr_msg)

                # 5回同じQRコードが見えたらコマンド送信する処理
                try:
                    if qr_msg != "":    # qr_msgが空(QRコードが１枚も認識されなかった)場合は何もしない
                        if qr_msg == pre_qr_msg:   # 今回認識したqr_msgが前回のpre_qr_msgと同じ時には処理
                            cnt_qr_msg+=1          # 同じQRコードが見えてる限りはカウンタを増やす

                            if cnt_qr_msg > 5:		# 50回同じQRコードが続いたら，コマンドを確定する
                                print('QR code 認識 : %s' % (qr_msg) )
                                cmds = qr_msg
                                cmd_len = len(cmds)
                                cmd_index = 0
                                auto_mode = 1	# 自動制御を有効にする
                                
                                print(cmd_len)

                                cnt_qr_msg = 0	# コマンド送信したらカウント値をリセット
                        else:
                            cnt_qr_msg = 0

                        pre_qr_msg = qr_msg	# 前回のpre_qr_msgを更新する

                    else:
                        cnt_qr_msg = 0	# 何も見えなくなったらカウント値をリセット

                except ValueError as e:	# if qr_msg != None の処理で時々エラーが出るので，try exceptで捕まえて無視させる
                    print("ValueError")


            # 自動制御フラグがON(=1)のときは，コマンド処理だけを行う
            if auto_mode == 1:
                if cmd_index < cmd_len:
                    print( cmds[cmd_index] )
                    key = cmds[cmd_index]	# commandsの中には'TLfblrudwcW'のどれかの文字が入っている
                    if key == 'T':
                        tello.takeoff()				# 離陸
                        time.sleep(5)
                    elif key == 'L':
                        flag = 0
                        tello.land()				# 着陸
                        time.sleep(4)
                    elif key == 'u':
                        tello.move_up(50)			# 上昇
                    elif key == 'd':
                        tello.move_down(50)		# 下降
                    elif key == 'c':
                        tello.rotate_counter_clockwise(45)		# 左旋回
                    elif key == 'w':
                        tello.rotate_clockwise(45)			# 右旋回
                    elif key == 'f':
                        tello.move_forward(50)		# 前進
                    elif key == 'b':
                        tello.move_back(50)	# 後進
                    elif key == 'l':
                        tello.move_left(50)		# 左移動
                    elif key == 'r':
                        tello.move_right(50)		# 右移動
                    elif key == 'W':
                        time.sleep(5)		# ウェイト

                    cmd_index += 1
                
                else:
                    cmd_len = 0
                    cmd_index = 0
                    auto_mode = 0

                pre_time = time.time()


            # (X) ウィンドウに表示
            cv2.imshow('OpenCV Window', small_image)    # ウィンドウに表示するイメージを変えれば色々表示できる

            # (Y) OpenCVウィンドウでキー入力を1ms待つ
            key = cv2.waitKey(1) & 0xFF
            if key == 27:                   # key が27(ESC)だったらwhileループを脱出，プログラム終了
                break
            elif key == ord('t'):           # 離陸
                tello.takeoff()
            elif key == ord('l'):           # 着陸
                tello.send_rc_control( 0, 0, 0, 0 )
                tello.land()
            elif key == ord('w'):           # 前進 30cm
                tello.move_forward(30)
            elif key == ord('s'):           # 後進 30cm
                tello.move_back(30)
            elif key == ord('a'):           # 左移動 30cm
                tello.move_left(30)
            elif key == ord('d'):           # 右移動 30cm
                tello.move_right(30)
            elif key == ord('e'):           # 旋回-時計回り 30度
                tello.rotate_clockwise(30)
            elif key == ord('q'):           # 旋回-反時計回り 30度
                tello.rotate_counter_clockwise(30)
            elif key == ord('r'):           # 上昇 30cm
                tello.move_up(30)
            elif key == ord('f'):           # 下降 30cm
                tello.move_down(30)
            elif key == ord('p'):           # ステータスをprintする
                print(tello.get_current_state())
            elif key == ord('m'):           # モータ始動/停止を切り替え
                if motor_on == False:       # 停止中なら始動 
                    tello.turn_motor_on()
                    motor_on = True
                else:                       # 回転中なら停止
                    tello.turn_motor_off()
                    motor_on = False
            elif key == ord('c'):           # カメラの前方/下方の切り替え
                if camera_dir == Tello.CAMERA_FORWARD:     # 前方なら下方へ変更
                    tello.set_video_direction(Tello.CAMERA_DOWNWARD)
                    camera_dir = Tello.CAMERA_DOWNWARD     # フラグ変更
                else:                                      # 下方なら前方へ変更
                    tello.set_video_direction(Tello.CAMERA_FORWARD)
                    camera_dir = Tello.CAMERA_FORWARD      # フラグ変更
                time.sleep(0.5)     # 映像が切り替わるまで少し待つ

            # (Z) 10秒おきに'command'を送って、死活チェックを通す
            current_time = time.time()                          # 現在時刻を取得
            if current_time - pre_time > 10.0 :                 # 前回時刻から10秒以上経過しているか？
                tello.send_command_without_return('command')    # 'command'送信
                pre_time = current_time                         # 前回時刻を更新


    except( KeyboardInterrupt, SystemExit):    # Ctrl+cが押されたら離脱
        print( "Ctrl+c を検知" )

    # 終了処理部
    cv2.destroyAllWindows()                             # すべてのOpenCVウィンドウを消去
    #tello.set_video_direction(Tello.CAMERA_FORWARD)     # カメラは前方に戻しておく
    tello.streamoff()                                   # 画像転送を終了(熱暴走防止)
    frame_read.stop()                                   # 画像受信スレッドを止める

    del tello.background_frame_read                    # フレーム受信のインスタンスを削除    
    del tello                                           # telloインスタンスを削除


# "python3 main_qr_read.py"として実行された時だけ動く様にするおまじない処理
if __name__ == "__main__":      # importされると__name_に"__main__"は入らないので，pyファイルが実行されたのかimportされたのかを判断できる．
    main()    # メイン関数を実行

