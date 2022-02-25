#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from djitellopy import Tello    # DJITelloPyのTelloクラスをインポート
import time                     # time.sleepを使いたいので
import cv2                      # OpenCVを使うため

# メイン関数
def main():
    # 初期化部
    # OpenCVが持つARマーカーライブラリ「aruco」を使う
    aruco = cv2.aruco
    dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)   # ARマーカーは「4x4ドット，ID番号50まで」の辞書を使う

    pre_idno = None     # 前回のID番号を記憶する変数
    count = 0           # 同じID番号が見えた回数を記憶する変数

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
            # ARマーカーの検出と，枠線の描画
            corners, ids, rejectedImgPoints = aruco.detectMarkers(small_image, dictionary) #マーカを検出
            aruco.drawDetectedMarkers(small_image, corners, ids, (0,255,0)) #検出したマーカ情報を元に，原画像に描画する

            # 30回同じマーカーが見えたらコマンド送信する処理
            try:
                if ids != None: # idsが空(マーカーが１枚も認識されなかった)場合は何もしない
                    idno = ids[0,0] # idsには複数のマーカーが入っているので，0番目のマーカーを取り出す

                    if idno == pre_idno:    # 今回認識したidnoが前回のpre_idnoと同じ時には処理
                        count+=1            # 同じマーカーが見えてる限りはカウンタを増やす

                        if count > 30:      # 50回同じマーカーが続いたら，コマンドを確定する
                            print("ID=%d"%(idno))

                            if idno == 0:
                                tello.takeoff()             # 離陸
                            elif idno == 1:
                                tello.land()                # 着陸
                                time.sleep(3)               # 着陸完了までのウェイト
                            elif idno == 2:
                                tello.move_up(30)           # 上昇
                            elif idno == 3:
                                tello.move_down(30)         # 下降
                            elif idno == 4:
                                tello.rotate_counter_clockwise(30)        # 左旋回
                            elif idno == 5:
                                tello.rotate_clockwise(30)         # 右旋回
                            elif idno == 6:
                                tello.move_forward(30)      # 前進
                            elif idno == 7:
                                tello.move_back(30)     # 後進
                            elif idno == 8:
                                tello.move_left(30)         # 左移動
                            elif idno == 9:
                                tello.move_right(30)        # 右移動

                            count = 0   # コマンド送信したらカウント値をリセット
                    else:
                        count = 0

                    pre_idno = idno # 前回のpre_idnoを更新する
                else:
                    count = 0   # 何も見えなくなったらカウント値をリセット

            except ValueError as err:   # if ids != None の処理で時々エラーが出るので，try exceptで捕まえて無視させる
                print("ValueError")

            # (X) ウィンドウに表示
            cv2.imshow('OpenCV Window', small_image)    # ウィンドウに表示するイメージを変えれば色々表示できる

            # (Y) OpenCVウィンドウでキー入力を1ms待つ
            key = cv2.waitKey(1) & 0xFF
            if key == 27:                   # key が27(ESC)だったらwhileループを脱出，プログラム終了
                break
            elif key == ord('t'):           # 離陸
                tello.takeoff()
            elif key == ord('l'):           # 着陸
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

    except( KeyboardInterrupt, SystemExit):    # Ctrl+cが押されたらループ脱出
        print( "Ctrl+c を検知" )

    # 終了処理部
    cv2.destroyAllWindows()                             # すべてのOpenCVウィンドウを消去
    tello.set_video_direction(Tello.CAMERA_FORWARD)     # カメラは前方に戻しておく
    tello.streamoff()                                   # 画像転送を終了(熱暴走防止)
    frame_read.stop()                                   # 画像受信スレッドを止める

    del tello.background_frame_read                    # フレーム受信のインスタンスを削除    
    del tello                                           # telloインスタンスを削除


# "python3 main_core.py"として実行された時だけ動く様にするおまじない処理
if __name__ == "__main__":      # importされると__name_に"__main__"は入らないので，pyファイルが実行されたのかimportされたのかを判断できる．
    main()    # メイン関数を実行
