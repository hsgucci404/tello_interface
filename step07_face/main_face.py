#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from djitellopy import Tello    # DJITelloPyのTelloクラスをインポート
import time                     # time.sleepを使いたいので
import cv2                      # OpenCVを使うため

# メイン関数
def main():
    # 初期化部
    # カスケード分類器の初期化
    cascPath = 'haarcascade_frontalface_alt.xml'    # 分類器データはローカルに置いた物を使う
    faceCascade = cv2.CascadeClassifier(cascPath)   # カスケードクラスの作成

    cnt_frame = 0   # フレーム枚数をカウントする変数
    pre_faces = []  # 顔検出結果を格納する変数

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

    # SDKバージョンを問い合わせ
    sdk_ver = tello.query_sdk_version()

    # モータとカメラの切替フラグ
    motor_on = False                    # モータON/OFFのフラグ
    camera_dir = Tello.CAMERA_FORWARD   # 前方/下方カメラの方向のフラグ

    # 前回強制終了して下方カメラかもしれないので
    if sdk_ver == '30':                                     # SDK 3.0に対応しているか？ 
        tello.set_video_direction(Tello.CAMERA_FORWARD)     # カメラは前方に
    # 自動モードフラグ
    auto_mode = 0

    time.sleep(0.5)     # 通信が安定するまでちょっと待つ

    # ループ部
    # Ctrl+cが押されるまでループ
    try:
        # 永久ループで繰り返す
        while True:

            # (1) 画像取得
            image = frame_read.frame    # 映像を1フレーム取得しimage変数に格納

            # (2) 画像サイズ変更と、カメラ方向による回転
            small_image = cv2.resize(image, dsize=(480,360) )   # 画像サイズを半分に変更

            if camera_dir == Tello.CAMERA_DOWNWARD:     # 下向きカメラは画像の向きが90度ずれている
                small_image = cv2.rotate(small_image, cv2.ROTATE_90_CLOCKWISE)      # 90度回転して、画像の上を前方にする

            # (3) ここから画像処理
            # 5フレームに１回顔認識処理をする
            if cnt_frame >= 5:
                # 顔検出のためにグレイスケール画像に変換，ヒストグラムの平坦化もかける
                gray_image = cv2.cvtColor(small_image, cv2.COLOR_BGR2GRAY)
                gray_image = cv2.equalizeHist( gray_image )

                # 顔検出
                faces = faceCascade.detectMultiScale(gray_image, 1.1, 3, 0, (10, 10))

                # 検出結果を格納
                pre_faces = faces

                cnt_frame = 0   # フレーム枚数をリセット

            # 顔の検出結果が空なら，何もしない
            if len(pre_faces) == 0:
                pass
            else:   # 顔があるなら続けて処理
                # 検出した顔に枠を書く
                for (x, y, w, h) in pre_faces:
                    cv2.rectangle(small_image, (x, y), (x+w, y+h), (0, 255, 0), 2)

                # １個めの顔のx,y,w,h,顔中心cx,cyを得る
                x = pre_faces[0][0]
                y = pre_faces[0][1]
                w = pre_faces[0][2]
                h = pre_faces[0][3]
                cx = int( x + w/2 )
                cy = int( y + h/2 )

                # 自動制御フラグが1の時だけ，Telloを動かす
                if auto_mode == 1:
                    a = b = c = d = 0   # rcコマンドの初期値は0

                    # 目標位置との差分にゲインを掛ける（P制御)
                    dx = 0.3 * (240 - cx)       # 画面中心との差分
                    dy = 0.3 * (180 - cy)       # 画面中心との差分
                    dw = 0.4 * (80 - w)        # 基準顔サイズ100pxとの差分

                    dx = -dx # 制御方向が逆だったので，-1を掛けて逆転させた

                    print('dx=%f  dy=%f  dw=%f'%(dx, dy, dw) )  # printして制御量を確認できるように

                    # 旋回方向の不感帯を設定
                    d = 0.0 if abs(dx) < 20.0 else dx   # ±20未満ならゼロにする
                    # 旋回方向のソフトウェアリミッタ(±100を超えないように)
                    d =  100 if d >  100.0 else d
                    d = -100 if d < -100.0 else d

                    # 前後方向の不感帯を設定
                    b = 0.0 if abs(dw) < 10.0 else dw   # ±10未満ならゼロにする
                    # 前後方向のソフトウェアリミッタ
                    b =  100 if b >  100.0 else b
                    b = -100 if b < -100.0 else b


                    # 上下方向の不感帯を設定
                    c = 0.0 if abs(dy) < 30.0 else dy   # ±30未満ならゼロにする
                    # 上下方向のソフトウェアリミッタ
                    c =  100 if c >  100.0 else c
                    c = -100 if c < -100.0 else c

                    # rcコマンドを送信
                    #drone.send_command('rc %s %s %s %s'%(int(a), int(b), int(c), int(d)) )
                    tello.send_rc_control( int(a), int(b), int(c), int(d) )

            cnt_frame += 1  # フレームを+1枚

            # (4) ウィンドウに表示
            cv2.imshow('OpenCV Window', small_image)    # ウィンドウに表示するイメージを変えれば色々表示できる

            # (5) OpenCVウィンドウでキー入力を1ms待つ
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
                if sdk_ver == '30':         # SDK 3.0に対応しているか？
                    if motor_on == False:       # 停止中なら始動 
                        tello.turn_motor_on()
                        motor_on = True
                    else:                       # 回転中なら停止
                        tello.turn_motor_off()
                        motor_on = False
            elif key == ord('c'):           # カメラの前方/下方の切り替え
                if sdk_ver == '30':         # SDK 3.0に対応しているか？
                    if camera_dir == Tello.CAMERA_FORWARD:     # 前方なら下方へ変更
                        tello.set_video_direction(Tello.CAMERA_DOWNWARD)
                        camera_dir = Tello.CAMERA_DOWNWARD     # フラグ変更
                    else:                                      # 下方なら前方へ変更
                        tello.set_video_direction(Tello.CAMERA_FORWARD)
                        camera_dir = Tello.CAMERA_FORWARD      # フラグ変更
                    time.sleep(0.5)     # 映像が切り替わるまで少し待つ
            elif key == ord('1'):
                auto_mode = 1                    # 追跡モードON
            elif key == ord('0'):
                tello.send_rc_control( 0, 0, 0, 0 )
                auto_mode = 0                    # 追跡モードOFF

            # (6) 10秒おきに'command'を送って、死活チェックを通す
            current_time = time.time()                          # 現在時刻を取得
            if current_time - pre_time > 10.0 :                 # 前回時刻から10秒以上経過しているか？
                tello.send_command_without_return('command')    # 'command'送信
                pre_time = current_time                         # 前回時刻を更新

    except( KeyboardInterrupt, SystemExit):    # Ctrl+cが押されたらループ脱出
        print( "Ctrl+c を検知" )

    # 終了処理部
    cv2.destroyAllWindows()                             # すべてのOpenCVウィンドウを消去
    
    if sdk_ver == '30':                                 # SDK 3.0に対応しているか？
        tello.set_video_direction(Tello.CAMERA_FORWARD) # カメラは前方に戻しておく

    tello.streamoff()                                   # 画像転送を終了(熱暴走防止)
    frame_read.stop()                                   # 画像受信スレッドを止める

    del tello.background_frame_read                     # フレーム受信のインスタンスを削除    
    del tello                                           # telloインスタンスを削除

# "python3 main_core.py"として実行された時だけ動く様にするおまじない処理
if __name__ == "__main__":      # importされると__name_に"__main__"は入らないので，pyファイルが実行されたのかimportされたのかを判断できる．
    main()    # メイン関数を実行
