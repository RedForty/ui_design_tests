from Qt import QtGui, QtCore, QtCompat, QtWidgets, __binding__
from Qt.QtGui import QPen, QColor, QBrush, QLinearGradient
# import maya.utils as utils


class SuperButton(QtWidgets.QPushButton):
    # All the animation setup here...
    # This is the flashes of white and green
    _explode_color_sequence_base = [
                                    [100, 255, 200], 
                                    [  5, 184, 204],
                                    [240, 255, 240],
                                    [  5, 184, 204]
                                   ]
    # This is the flashes plus the descending alpha
    _explode_alpha_sequence = [255,   0, 255,   0, 255, 255, 254, 252, 249, 243,
                               234, 221, 200, 164,  96,  41,  17,   6,   2,   0]
    _pens_text = {}
    _animated_brush = {}
    value = []                               
    # Comp the lists together so I don't have to do it manually. Ugly list.
    # Make the pen dict
    for i in range(20): 
        value = [255, 255, 255]
        value.append(_explode_alpha_sequence[i])
        _pens_text[i+1] = QPen(QColor(*value), 1, QtCore.Qt.SolidLine)
    # And then add the standard pen color at index 0
    _pens_text[0] = QPen(QtGui.QColor(255, 255, 255), 1, QtCore.Qt.SolidLine)
    # _pens_text[0] = QPen(QtGui.QColor(202, 207, 210), 1, QtCore.Qt.SolidLine)

    _pens_text_disabled   = QPen(QColor(102, 107, 110), 1, QtCore.Qt.SolidLine)
    _pens_clear  = QPen(QColor(  0, 0, 0,  0), 1, QtCore.Qt.SolidLine)
    
    _active_color = QColor(5, 184, 204) # The hot blue active color
    _background_color = QColor(85, 85, 85) # For the button when in focus
    
    # Make the brushes dict
    for i in range(20): 
        try:
            value = list(_explode_color_sequence_base[i])
        except:
            value = list(_explode_color_sequence_base[-1])
        value.append(_explode_alpha_sequence[i])
        _animated_brush[i+1] = QBrush(QColor(*value))
    # And then add the standard brush color at index 0
    _animated_brush[0] = QBrush(QtGui.QColor(85, 85, 85, 255))

    explodeComplete      = QtCore.Signal(bool)

    def __init__(self, *args, **kwargs):
        '''
        Super button has a progressBarChunk attribute from 0-1
        '''
        QtWidgets.QPushButton.__init__(self, *args, **kwargs)
        # self._radius = 5
        self._progressEnabled = False
        self.progressBarChunk = 0.0
        self.color = QColor(0, 0, 0)
        self._progressFinished = False

        self._progress_cooldown = False
        self._animate_index = 0
        self._anim_timer = QtCore.QTimer()
        self._anim_timer.timeout.connect(self._animateButtonCooldown)

    # ------------------------------------------------------------------------ #

    def paintEvent(self, *args):
        # super(self.__class__, self).paintEvent(event) # Don't break the original
        if self._progressEnabled == False and self._progress_cooldown == False:
            QtWidgets.QPushButton.paintEvent(self, *args) # Act normally
            return

        painter = QtWidgets.QStylePainter(self)
        option  = QtWidgets.QStyleOption()

        option.initFrom(self)      

        x = option.rect.x()
        y = option.rect.y()
        topleft = option.rect.topLeft()
        topRight = option.rect.topRight()
        height = option.rect.height() - 1
        width  = option.rect.width()  - 1 
        radius = 8

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing)

        # Render progressbar on button background ---------------------------- #

        if self._progressEnabled == True:
            gradient = QLinearGradient(0, 0, width, 0)
            gradient.setColorAt(0.0, self._active_color)
            if self.progressBarChunk >=.95:
                gradient.setColorAt(1.0, self._active_color)
            else:
                gradient.setColorAt(self.progressBarChunk, self._active_color)
                gradient.setColorAt(self.progressBarChunk + .001, self._background_color) # QtCore.Qt.transparent) # self._background_color) #

            painter.setPen(self._pens_clear)
            painter.setBrush(gradient)
            painter.drawRoundedRect(QtCore.QRect(x, y, width, height), radius, radius)

        # Exploding button---------------------------------------------------- #

        if self._progress_cooldown == True:
            # The animate part
            painter.setPen(self._pens_clear)
            painter.setBrush(self._animated_brush[self._animate_index])
            painter.drawRoundedRect(QtCore.QRect(x, y, width, height), radius, radius)

        # draw text ---------------------------------------------------------- #

        text = self.text()
        if text == '': return

        alignment = (QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        painter.setPen(self._pens_text[self._animate_index])
        painter.drawText(x, y, width, height + 1, alignment, text)


    # ------------------------------------------------------------------------ #

    def explodeButton(self):
        if self._anim_timer.isActive():
            return
        self._progress_cooldown = True
        self._animate_index = 0
        self._anim_timer.start(30)


    def _animateButtonCooldown(self):
        if self._progress_cooldown:
            if self._animate_index >= 20:
                self._animate_index = 20
                self._progress_cooldown = False # Stop climbing at this point
                self.explodeComplete.emit(True)
            else:
                self._animate_index += 1
        else:
            self._anim_timer.stop()
            self._animate_index = 0
        self.update()
        # utils.executeDeferred(self.update) # TODO - Discover if we need this

    # ------------------------------------------------------------------------ #

