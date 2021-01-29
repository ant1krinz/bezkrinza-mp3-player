import sys
from PyQt5 import uic, QtCore
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, \
    QMessageBox, QStyle, QFormLayout, QGroupBox, QLabel, \
    QPushButton, QWidget, QInputDialog, QGridLayout, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
import sqlite3
from mutagen.mp3 import MP3
from pygame import mixer, event
import eyed3
from random import choice

mixer.init()


class Player(QMainWindow):
    def __init__(self):
        super(Player, self).__init__()
        uic.loadUi("player_interface.ui", self)
        self.add_music_button.clicked.connect(self.add_music)

        self.setWindowTitle("BEZKRINZA MP3-PLAYER")

        self.list_of_all_buttons = []

        # настройки кнопки play
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.play_pause_track)
        self.play_button.setEnabled(False)

        self.setWindowIcon(QIcon("logo player.png"))

        self.setFixedSize(1050, 600)

        # настройки внешнего вида и функционала кнопок левый/правый трек
        self.right_track_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.left_track_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.right_track_button.setEnabled(False)
        self.left_track_button.setEnabled(False)
        self.right_track_button.clicked.connect(self.next_track)
        self.left_track_button.clicked.connect(self.previous_track)

        self.random_track_button.clicked.connect(self.choose_random_music)
        self.random_track_button.setEnabled(False)

        self.playing = False

        # словари, в которых будут в качестве ключей храниться кнопки delete и play, которые находятся
        # в scrollarea, а значениями будут id треков, соответствующих этим кнопкам
        self.button_slovar = {}
        self.button_del_slovar = {}

        # настройка функционала и внешнего вида ползунков
        self.volume_slider.valueChanged[int].connect(self.change_volume)
        self.volume_slider.setRange(0, 10)
        self.volume_slider.setValue(5)
        self.content_slider.sliderMoved[int].connect(self.change_content)

        self.new_playlist_id = 1

        self.info_button.clicked.connect(self.show_info)

        self.add_playlist_button.clicked.connect(self.add_playlist)

        self.playlists_list = ["Основной"]

        self.update_scrollarea()

        self.playlists.addItem("Основной")
        self.update_combobox()

        self.playlists.currentTextChanged.connect(self.change_playlist)

        self.change_color_button.clicked.connect(self.change_color_theme)

        self.theme = "Dark"

        # создание и настройка таймеров: ежесекундного и замеряющего время до конца трека
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_track)
        self.slider_timer = QTimer(self)
        self.slider_timer.setInterval(1000)
        self.slider_timer.timeout.connect(self.move_content_slider)

        self.artist = ''
        self.title = ''

    # метод, вызываемый для остановки/продолжения воспроизведения трека
    def play_pause_track(self):
        # проверка флага
        if not self.playing:
            mixer.music.unpause()
            # изменение значения флага
            self.playing = True
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            # остановка и повторный запуск таймеров
            self.timer.stop()
            delta = self.length * 1000 - mixer.music.get_pos()
            self.timer.start(delta)
            self.slider_timer.start()

        else:
            mixer.music.pause()
            # изменение значения флага
            self.playing = False
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            # остановка таймеров
            self.timer.stop()
            self.timer.stop()
            self.slider_timer.stop()

    # изменение позиции проигрывания трека
    def change_content(self, value):
        mixer.music.set_pos(float(value))
        # запуск таймера с новым значением времени, оставшегося до конца
        self.timer.stop()
        delta = self.length * 1000 - value * 1000
        self.timer.start(delta)

    # изменение громкости, играющего трека в зависимости от установленной громкости (по умолчанию 50%)
    def change_volume(self, value):
        mixer.music.set_volume(float(value / 10))

    # добавление данных о новом треке в БД/выбор трека
    def add_music(self):
        fname = QFileDialog.getOpenFileName(self, 'choose mp3 file', '', 'Звук в формате MP3 (*.mp3)')[0]
        # проверка наличия выбранного файла
        if fname:
            audio_file = eyed3.load(fname)
            song = MP3(fname)
            # получаем данные о длине трека (минуты)
            length = int(song.info.length)
            # проверка наличия в файле данных об исполнителе и названии
            if audio_file.tag.title != None:
                title = audio_file.tag.title
            else:
                title = "Неизвестно"

            if audio_file.tag.artist != None:
                artist_name = audio_file.tag.artist

            else:
                artist_name = "Неизвестен"
            # создаю jpg с обложкой
            with open("{} - {}.jpg".format(artist_name, title), "wb") as image_file:
                if list(audio_file.tag.images) != []:
                    image_name = "{} - {}.jpg".format(artist_name, title)
                    image_file.write(audio_file.tag.images[0].image_data)
                else:
                    image_name = "none_photo.png"
            # заношу все в БД
            con = sqlite3.connect("database_player.db")
            cur = con.cursor()
            result = cur.execute("""INSERT INTO tracks(artist,title,length,path_to_track, path_to_image, playlist) 
                                   VALUES (?,?,?,?,?,?)""",
                                 (artist_name, title, length, fname, image_name, self.new_playlist_id)).fetchall()
            con.commit()
            con.close()

            self.update_scrollarea()

    # изменение данных в scrollarea
    def update_scrollarea(self):
        # внешний главный layout
        self.layout = QFormLayout(self)
        # groupbox для занесения layout в scrollarea
        self.groupBox = QGroupBox(self)
        # списки всех кнопок delete, play и строчек с названиями и исполнителями
        self.list_label = []
        self.list_button = []
        self.list_del_button = []
        con = sqlite3.connect("database_player.db")
        cur = con.cursor()
        result = cur.execute("""SELECT id, artist, title FROM tracks 
                            WHERE playlist = ?""", (self.new_playlist_id,)).fetchall()

        i = 0
        # внутренний layout
        hlayout = QGridLayout(self)
        for elem in result:
            # обрабатываю данные, полученные по запросу в БД
            id = elem[0]
            artist = elem[1]
            title = elem[2]

            # заношу данные в списки
            self.list_label.append(QLabel("{} - {}".format(artist, title), self))
            self.list_button.append(QPushButton(self))
            self.list_del_button.append(QPushButton(self))

            # заношу виджеты кнопок, названия во вонутренний layout
            hlayout.addWidget(self.list_label[i], i, 0)
            hlayout.addWidget(self.list_button[i], i, 1)
            hlayout.addWidget(self.list_del_button[i], i, 2)

            # привязываю к кнопкам методы
            self.list_button[i].clicked.connect(self.start_music)
            self.list_del_button[i].clicked.connect(self.delete_music)

            # настраиваю внешний вид
            self.list_del_button[i].setIcon(QIcon("bin.png"))
            self.list_button[i].setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

            # заношу виджеты как ключ в словарь и присваиваю им всем id
            self.button_slovar[str(self.list_button[i])] = id
            self.button_del_slovar[str(self.list_del_button[i])] = id

            # настраиваю внешний вид виджетов
            self.list_label[i].setFont(QFont("Century Gothic", 10, QFont.Bold))
            self.list_del_button[i].setStyleSheet('QPushButton {background-color: rgb(130, 130, 130);'
                                                  'border-radius: 8px}')
            self.list_button[i].setStyleSheet('QPushButton {background-color: rgb(130, 130, 130);'
                                              'border-radius: 8px}')

            i += 1
        # заношу внутренний layout во внешний, чтобы убрать образовывающиеся пробелы во внутреннем layout
        self.layout.addRow(hlayout)
        self.groupBox.setLayout(self.layout)
        # добавляю в scrollarea groupbox со внешним layout
        self.music_scroller.setWidget(self.groupBox)
        con.commit()
        con.close()

    # удаление музыки
    def delete_music(self):
        con = sqlite3.connect("database_player.db")
        cur = con.cursor()
        # определяю, кто отправил сигнал и достаю из словаря соответствующий id
        btn = str(self.sender())
        id = self.button_del_slovar[btn]
        # удаляю данные из БД
        result = cur.execute("""DELETE from tracks WHERE id = ?""", (id,)).fetchall()
        con.commit()
        con.close()
        self.update_scrollarea()

    # начало проигрывания музыки
    def start_music(self, new_id=-1):
        con = sqlite3.connect("database_player.db")
        cur = con.cursor()
        # проверка, был ли послан сигнал по нажатию кнопки next_track, кнопки play в scrollarea или автоматически
        # при заверешении предыдущего трека
        if not new_id:
            btn = str(self.sender())
            self.playing_id = self.button_slovar[btn]
            result = cur.execute("""SELECT artist,title,length,path_to_track,path_to_image FROM tracks 
                                        WHERE id = ?""", (self.playing_id,)).fetchall()

        else:
            result = cur.execute("""SELECT artist,title,length,path_to_track,path_to_image FROM tracks 
                                                    WHERE id = ?""", (new_id,)).fetchall()
            self.playing_id = new_id

        # Обрабатываю данные из БД
        self.artist = result[0][0]
        self.title = result[0][1]
        self.length = result[0][2]
        self.current_path = result[0][3]
        # задаю интервал таймеру равный длине трека (мсек) и запускаю его
        self.timer.setInterval(self.length * 1000)
        self.timer.start()
        image = result[0][4]
        con.close()
        mixer.music.load(self.current_path)
        mixer.music.play()
        # изменяю значение флага
        self.playing = True
        mixer.music.set_volume(0.5)
        self.content_slider.setRange(0, int(self.length - 1))
        self.volume_slider.setValue(5)
        # устанавливаю обложку альбома
        self.pixmap = QPixmap(image)
        self.image.setPixmap(self.pixmap)
        # проверяю, какого цвета надо установить шрифт, в зависимости от темы
        if self.theme == "Dark":
            self.playing_song_artist.setText("<span style='color: rgb(255, 255, 255);'>{}</span>".format(self.artist))
            self.playing_song_title.setText("<span style='color: rgb(255, 255, 255);'>{}</span>".format(self.title))
        else:
            self.playing_song_artist.setText("<span style='color: rgb(0, 0, 0);'>{}</span>".format(self.artist))
            self.playing_song_title.setText("<span style='color: rgb(0, 0, 0);'>{}</span>".format(self.title))
        # возваращаю ползунок песни в начало
        self.content_slider.setValue(0)
        # делаб все кнопки нажимаемы (нужно при запуске первого трека)
        self.play_button.setEnabled(True)
        self.right_track_button.setEnabled(True)
        self.left_track_button.setEnabled(True)
        self.random_track_button.setEnabled(True)
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        # запускаю секнудный таймер
        self.slider_timer.start()

    # отображение информации о приложении
    def show_info(self):
        app_info = QMessageBox()
        app_info.setWindowTitle("Info")
        app_info.setWindowIcon(QIcon("info.png"))
        app_info.setText("В данный момент вы используете MP3-плейер bezkrinza. "
                         "В этом плейере вы можете в один клик добавить новый плейлист(кнопка ADD PLAYLIST),"
                         "добавить в него свои любимые треки(кнопка ADD MUSIC). Если же они вам наскучат, "
                         "вы сможете их удалить(кнопка delete справа от названия трека в виджете со всеми песянми, "
                         "добавленными в плейлист). Также присутствует возможность включить рандомный трек из играющего"
                         "в данный момент плейлиста(кнопка random_track справа от панели управления).\n"
                         "Приложение разработал Куценко Дмитрий\n"
                         "Все права защищены")

        app_info.setStyleSheet(
            """
            QMessageBox {
                font: Century Gothic 20px;
                color: rgb(255, 255, 255);        
                background-color: rgb(255, 255, 255);
            }         
            """
        )
        info_window = app_info.exec_()

    # добавление новых плейлистов
    def add_playlist(self):
        # диалог с вводомназвания нового плейлиста
        playlist_name, ok_pressed = QInputDialog.getText(self, "New Playlist Name",
                                                         "Введите название нового плейлиста")
        # проверка нажатия кнопки ОК
        if ok_pressed:
            # обновляю данные в БД
            con = sqlite3.connect("database_player.db")
            cur = con.cursor()
            result = cur.execute("""INSERT INTO playlists(playlist_name) VALUES(?)""", (playlist_name,))
            con.commit()
            con.close()
            self.update_combobox()

    # изменение списка отображаемых плейлистов в combobox
    def update_combobox(self):
        con = sqlite3.connect("database_player.db")
        cur = con.cursor()
        result = cur.execute("""SELECT playlist_name FROM playlists""").fetchall()
        for elem in result:
            # проверка наличия элемента в combobox
            if elem[0] not in self.playlists_list:
                self.playlists.addItem(elem[0])
                self.playlists_list.append(elem[0])

    # изменение данных о выбранном плейлисте
    def change_playlist(self):
        new_playlist_name = self.playlists.currentText()
        con = sqlite3.connect("database_player.db")
        cur = con.cursor()
        self.new_playlist_id = cur.execute("""SELECT id FROM playlists 
                                           WHERE playlist_name = ?""", (new_playlist_name,)).fetchall()[0][0]
        con.commit()
        con.close()
        self.update_scrollarea()

    # начало проигрывания следующего трека в плейлисте
    # если трек всего один, он начнет проигрываться заново
    def next_track(self):
        try:
            con = sqlite3.connect("database_player.db")
            cur = con.cursor()
            # получаю данные об айди играющего сейчас плейлиста
            current_playlist_id = cur.execute("""SELECT playlist FROM tracks 
                                     WHERE id = ?""", (self.playing_id,)).fetchall()[0][0]
            result = cur.execute("""SELECT id FROM tracks 
                                           WHERE playlist = ?""", (current_playlist_id,)).fetchall()
            # список айди всех треков плейлиста
            list_of_ids = [elem[0] for elem in result]

            # проверка длины плейлиста
            if len(list_of_ids) == 1:
                self.start_music(new_id=self.playing_id)

            else:
                if list_of_ids.index(int(self.playing_id)) == len(list_of_ids) - 1:
                    self.playing_id = list_of_ids[0]
                    self.start_music(new_id=list_of_ids[0])
                else:
                    ind = list_of_ids.index(self.playing_id)
                    self.playing_id = list_of_ids[ind + 1]
                    self.start_music(new_id=list_of_ids[ind + 1])
        except Exception:
            pass

    # аналогично с next_track поигрывет предыдущий трек
    def previous_track(self):
        try:
            con = sqlite3.connect("database_player.db")
            cur = con.cursor()
            current_playlist_id = cur.execute("""SELECT playlist FROM tracks 
                                     WHERE id = ?""", (self.playing_id,)).fetchall()[0][0]
            result = cur.execute("""SELECT id FROM tracks 
                                           WHERE playlist = ?""", (current_playlist_id,)).fetchall()
            list_of_ids = [elem[0] for elem in result]

            if len(list_of_ids) == 1:
                self.start_music(new_id=self.playing_id)

            else:
                if list_of_ids.index(int(self.playing_id)) == 0:
                    self.playing_id = list_of_ids[-1]
                    self.start_music(new_id=list_of_ids[-1])
                else:
                    ind = list_of_ids.index(self.playing_id)
                    self.playing_id = list_of_ids[ind - 1]
                    self.start_music(new_id=list_of_ids[ind - 1])
        except Exception:
            pass

    # метод для автоматического движения ползунка во время проигрывания трека
    def move_content_slider(self):
        self.content_slider.setValue(self.content_slider.value() + 1)

    # изменение цветовой темы
    def change_color_theme(self):
        # вручную меняю оформление почти всех виджетов приложения
        if self.theme == "Dark":
            self.frame.setStyleSheet('QFrame {background-color: rgb(255, 255, 255)}')
            self.add_music_button.setStyleSheet('QPushButton {background-color: #7dff8c; border-radius: 20px}')
            self.add_playlist_button.setStyleSheet('QPushButton {background-color: #7dff8c; border-radius: 20px}')
            self.play_button.setStyleSheet('QPushButton {background-color: #7dff8c; border-radius: 15px}')
            self.right_track_button.setStyleSheet('QPushButton {background-color: #7dff8c; border-radius: 15px}')
            self.left_track_button.setStyleSheet('QPushButton {background-color: #7dff8c; border-radius: 15px}')
            self.info_button.setStyleSheet('QPushButton ''{background-color: #7dff8c; border-radius: 10px}')
            self.random_track_button.setStyleSheet('QPushButton ''{background-color: #7dff8c; border-radius: 10px}')
            self.change_color_button.setStyleSheet('QPushButton ''{background-color: #7dff8c; border-radius: 10px}')
            if self.artist and self.title:
                self.playing_song_artist.setText("<span style='color: rgb(0, 0, 0);'>{}</span>".format(self.artist))
                self.playing_song_title.setText("<span style='color: rgb(0, 0, 0);'>{}</span>".format(self.title))
            self.theme = "Light"

        else:
            self.frame.setStyleSheet('QFrame {background-color: rgb(52, 52, 52)}')
            self.add_music_button.setStyleSheet('QPushButton '
                                                '{background-color: rgb(23, 255, 58); border-radius: 20px}')
            self.add_playlist_button.setStyleSheet('QPushButton '
                                                   '{background-color: rgb(23, 255, 58); border-radius: 20px}')
            self.play_button.setStyleSheet('QPushButton '
                                           '{background-color: rgb(23, 255, 58); border-radius: 15px}')
            self.right_track_button.setStyleSheet('QPushButton '
                                                  '{background-color: rgb(23, 255, 58); border-radius: 15px}')
            self.left_track_button.setStyleSheet('QPushButton '
                                                 '{background-color: rgb(23, 255, 58); border-radius: 15px}')
            self.info_button.setStyleSheet('QPushButton '
                                           '{background-color: rgb(23, 255, 58); border-radius: 10px}')
            self.change_color_button.setStyleSheet('QPushButton '''
                                                   '{background-color: rgb(23, 255, 58); border-radius: 10px}')
            self.random_track_button.setStyleSheet('QPushButton '''
                                                   '{background-color: rgb(23, 255, 58); border-radius: 10px}')
            if self.artist and self.title:
                self.playing_song_artist.setText(
                    "<span style='color: rgb(255, 255, 255);'>{}</span>".format(self.artist))
                self.playing_song_title.setText("<span style='color: rgb(255, 255, 255);'>{}</span>".format(self.title))
            self.theme = "Dark"

    # генерация окна с подтверждением желания пользователя закрыть приложение
    def closeEvent(self, event):
        # месседж бокс с вопросом и двумя вариантами ответа
        reply = QMessageBox.question(self, 'Выход из программы', "Вы точно хотите закрыть плейер?",
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.Yes)

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    # выбор рандомного айди трека из играющего плейлиста и его запуск
    def choose_random_music(self):
        try:
            con = sqlite3.connect("database_player.db")
            cur = con.cursor()
            # получаю данные об айди играющего сейчас плейлиста
            current_playlist_id = cur.execute("""SELECT playlist FROM tracks 
                                             WHERE id = ?""", (self.playing_id,)).fetchall()[0][0]
            result = cur.execute("""SELECT id FROM tracks 
                                                   WHERE playlist = ?""", (current_playlist_id,)).fetchall()
            list_of_ids = [elem[0] for elem in result]
            # функцией choice выбираю рандомный айди
            self.start_music(new_id=choice(list_of_ids))
        except Exception:
            pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Player()
    ex.show()
    sys.exit(app.exec())
