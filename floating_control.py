from functools import partial
import maya.OpenMaya as om
import maya.OpenMayaUI as omui
from maya import cmds, mel
import math

from Qt import QtGui, QtCore, QtWidgets, QtCompat # pylint:disable=E0611

from ui_design_tests.push_button import SuperButton

import KlugTools # DELETE FOR DEPLOY

# =========================================================================== #
# Globals from KlugTools.ui_design_tests.floating_control import Interface_Test as ui_tool

# The size of the icon
HEIGHT = 50
WIDTH  = 120

ALPHA        = 255 * (0.25) # Change 0.25 to whatever percentage you want
RANGE_COLOR  = (150, 150, 150) # RGB
CTRL_COLOR   = (  0, 255,  50)
ALT_COLOR    = ( 80, 190, 255)
SHIFT_COLOR  = (255,  80, 200)

STICKY_RANGE = 5

# =========================================================================== #
# Helper functions ---------------------------------------------------------- #

def group(L):
    first = last = L[0]
    for n in L[1:]:
        if n - 1 == last: # Part of the group, bump the end
            last = n
        else: # Not part of the group, yield current group and start a new
            yield first, last
            first = last = n
    yield first, last # Yield the last group

def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))

def _get_maya_window():
    mayaMainWindowPtr = omui.MQtUtil.mainWindow()
    mayaMainWindow = QtCompat.wrapInstance(long(mayaMainWindowPtr), QtWidgets.QWidget)
    return mayaMainWindow

def _get_graphEditor():
    return QtCompat.wrapInstance(long(omui.MQtUtil.findControl('graphEditor1GraphEdImpl')), QtWidgets.QWidget)
    # return QtCompat.wrapInstance(long(omui.MQtUtil.findControl('graphEditor1GraphEd')), QtWidgets.QWidget)

def _get_time_widget():
    return QtCompat.wrapInstance(long(omui.MQtUtil.findControl(_get_time_control())), QtWidgets.QWidget)

def _get_time_control():
    return mel.eval('$tmpVar = $gPlayBackSlider')

def _get_timeline_range():
    time_range = cmds.timeControl(
        _get_time_control(), query=True, rangeArray=True)
    return range(int(time_range[0]), int(time_range[1]))

def get_qdistance(qpointA, qpointB):
    distance = math.sqrt((qpointB.x()-qpointA.x())**2+(qpointB.y()-qpointA.y())**2)
    return distance

# =========================================================================== #
# Event filter -------------------------------------------------------------- #


class UI_Event_Filter(QtCore.QObject):
    def __init__(self, parent):
        super(UI_Event_Filter, self).__init__()
        self._parent = parent
        self.cursor_start_position = QtGui.QCursor.pos()

    def check_modifiers(self):
        check = QtWidgets.QApplication.instance().queryKeyboardModifiers()
        ctrl = bool(QtCore.Qt.ControlModifier & check)
        alt = bool(QtCore.Qt.AltModifier & check)
        shift = bool(QtCore.Qt.ShiftModifier & check)
        self._parent.modifiers = [int(ctrl), int(alt), int(shift)]

    def check_clicks(self):
        check  = QtWidgets.QApplication.instance().mouseButtons()
        left   = bool(QtCore.Qt.LeftButton & check)
        middle = bool(QtCore.Qt.MiddleButton & check)
        right  = bool(QtCore.Qt.RightButton & check)
        self._parent.clicks = [int(left), int(middle), int(right)]

    def eventFilter(self, obj, event):
        if event.type() in [QtCore.QEvent.KeyPress,
                            QtCore.QEvent.KeyRelease]:
            if not event.isAutoRepeat():
                if event.key() in [QtCore.Qt.Key_Control,
                                   QtCore.Qt.Key_Alt,
                                   QtCore.Qt.Key_Shift,
                                   QtCore.Qt.Key_Meta]:
                    self._parent.previous_modifiers = self._parent.modifiers
                    self.check_modifiers()
                    if self._parent.modifiers != self._parent.previous_modifiers:
                        self._parent.modifier_changed()
                        # print self._parent.modifiers

        if event.type() == QtCore.QEvent.MouseButtonPress:
            self.check_clicks()
            self.cursor_start_position = QtGui.QCursor.pos()

            self._parent.mouse_activation_state = any(self._parent.clicks)
            return True

        if event.type() == QtCore.QEvent.MouseButtonRelease:
            self.check_clicks()

            self._parent.mouse_activation_state = any(self._parent.clicks)
            if self._parent.mouse_activation_state == False:
                self._parent.deactivate()
            return True

        if event.type() == QtCore.QEvent.MouseMove:
            if self._parent.mouse_activation_state == True:
                sticky_distance = get_qdistance(self.cursor_start_position,
                                                QtGui.QCursor.pos())
                if sticky_distance > STICKY_RANGE and self._parent.sticky_start == False:
                    self._parent.sticky_start = True
                    self._parent.cursor_start_position = QtGui.QCursor.pos()
                elif sticky_distance < STICKY_RANGE and self._parent.sticky_start == False:
                    print sticky_distance
                if self._parent.sticky_start:
                    self._parent.activate()
            else:
                self._parent.sticky_start = False

        if event.type() == QtCore.QEvent.ApplicationStateChange:
            self._parent.clicks = [0, 0, 0]
            self._parent.modifiers = [0, 0, 0]
            self._parent.stop()
            print 'Maya focus lost! Aborting!'

        return QtCore.QObject.eventFilter(self, obj, event)


class Interface_Test(QtWidgets.QWidget):

    UI_INSTANCE = None

    @classmethod
    def start(cls):
        if not cls.UI_INSTANCE:
            cls.UI_INSTANCE = Interface_Test()
        # cls.UI_INSTANCE.show()

    @classmethod
    def stop(cls):
        if cls.UI_INSTANCE:
            cls.UI_INSTANCE.close()
            cls.UI_INSTANCE.deleteLater()
            cls.UI_INSTANCE = None

    def __init__(self):
        super(Interface_Test, self).__init__()

        self.setObjectName("InterfaceTest03")
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowTransparentForInput
            | QtCore.Qt.WindowDoesNotAcceptFocus
            | QtCore.Qt.WA_ShowWithoutActivating
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.WindowSystemMenuHint
            | QtCore.Qt.SplashScreen
            | QtCore.Qt.Tool
        )

        self._ge_widget = _get_graphEditor()
        self.ui_event_filter = UI_Event_Filter(self)
        self.ge_event_filter = None
        self.region_range = _get_timeline_range()
        self.region_start_frame = cmds.currentTime(q=True)
        self.region_end_frame   = cmds.currentTime(q=True) + 1.0

        self.GE_Draw = GE_Overlay(self)
        self.update_ge_region()

        self.Timeline_Draw = Timeline_Overlay(self)
        self.update_timeline_region()

        self.mouse_activation_state  = False
        self.sticky_start            = False
        self.is_activated            = False
        self.activated_mouse_buttons = []
        self.activated_modifiers     = []
        self.previous_modifiers      = [] # For locking event spam
        self.feedback_text           = str(0)

        self.ctrl_border_color       = tuple(x+50 for x in CTRL_COLOR)
        self.alt_border_color        = tuple(x+50 for x in ALT_COLOR)
        self.shift_border_color      = tuple(x+50 for x in SHIFT_COLOR)

        self.active_color            = RANGE_COLOR # This is the one that will change with mods
        self.clicks                  = [0, 0, 0]
        self.modifiers               = [0, 0, 0]

        self.initUI()
        self.install_event_filters()

    def initUI(self):
        # print "Setting up UI"
        self.LYT_main = QtWidgets.QHBoxLayout()
        self.setLayout(self.LYT_main)
        self.LYT_main.setContentsMargins(0,0,0,0)
        self.LYT_main.setSpacing(0)
        # self.BTN_main = QtWidgets.QPushButton()
        self.BTN_main = SuperButton(self)
        self.BTN_main.setObjectName('BTN_main')
        self.BTN_main.setText(self.feedback_text)
        self.BTN_main.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed)
        self.LYT_main.addWidget(self.BTN_main)
        self.BTN_main.setMinimumSize(WIDTH, HEIGHT)
        self.LYT_main.setAlignment(
            QtCore.Qt.AlignTop | QtCore.Qt.AlignRight)

        self.setStyleSheet("""
                QPushButton#BTN_main{
                    color: rgb(150, 150, 150);
                    background-color: rgb(80, 80, 80);
                    border-style: solid;
                    border-width:2px;
                    margin: 0px;
                    padding: 0px;
                    border-color: rgb(20, 20, 30);
                    font: normal normal bold 40px/normal Impact, Charcoal, sans-serif;
                }""")

        self.update_widget_position()
        self.GE_Draw.show()
        self.Timeline_Draw.show()
        self.init_connections()

    def _explodeButton(self):
        self.BTN_main.show()
        self.BTN_main.explodeButton()

    def _explodeComplete(self, value):
        # self.activeButton.setText(self.activeButton_text)
        self.BTN_main.setText("DONE")
        self.BTN_main.hide()
        self.update()
        # print self.activeButton_text

    def _update_progress_bar(self, value):
        self.BTN_main._progressEnabled = True
        progressChunkCurrent = value / 500.0
        self.BTN_main.progressBarChunk = progressChunkCurrent
        # self.BTN_main.show()
        # self.BTN_main.raise_()
        self.update()

    def init_connections(self):
        self.BTN_main.explodeComplete.connect(self._explodeComplete)

    def install_event_filters(self):
        QtWidgets.QApplication.instance().installEventFilter(self.ui_event_filter)

    def uninstall_event_filters(self):
        QtWidgets.QApplication.instance().removeEventFilter(self.ui_event_filter)

    def showEvent(self, event):
        # print "showEvent"
        self.update_widget_position()
        QtWidgets.QApplication.instance().setOverrideCursor(QtCore.Qt.SplitHCursor)

    def hideEvent(self, event):
        # print "hideEvent"
        QtWidgets.QApplication.instance().restoreOverrideCursor()

    def closeEvent(self, event):
        # print "closeEvent"
        self.BTN_main.setText(str(0))
        self.GE_Draw.close()
        self.GE_Draw.deleteLater()
        self.Timeline_Draw.close()
        self.Timeline_Draw.deleteLater()

        QtWidgets.QApplication.instance().restoreOverrideCursor()
        self.uninstall_event_filters()
        self.deactivate()

    def update_widget_position(self):
        self.mouse_position = QtGui.QCursor.pos()
        self.setGeometry(
            self.mouse_position.x()+20,
            self.mouse_position.y()-80,
            WIDTH,
            HEIGHT
            )

    def activate(self):
        # print "activate"
        if self.is_activated == False:

            self.activated_mouse_buttons = []
            self.activated_modifiers = []

            if self.clicks[0] == 1:
                self.activated_mouse_buttons.append('left')
            if self.clicks[1] == 1:
                self.activated_mouse_buttons.append('right')
            if self.clicks[2] == 1:
                self.activated_mouse_buttons.append('middle')

            if self.modifiers[0] == 1:
                self.activated_modifiers.append('ctrl')
            if self.modifiers[1] == 1:
                self.activated_modifiers.append('alt')
            if self.modifiers[2] == 1:
                self.activated_modifiers.append('shift')

            self.is_activated = True

            print "Activating tool with {modifier_keys} and {mouse_buttons}.".format(
                modifier_keys = self.activated_modifiers,
                mouse_buttons = self.activated_mouse_buttons
            )

            if self.isHidden():
                self.show()
                self.raise_()

        # =~---------------------------------------------------------------~= #
        # Now do the main operation ----------------------------------------- #

        self.update_widget_position()
        self.feedback_text = self.cursor_start_position.x() - QtGui.QCursor.pos().x()
        self.BTN_main.setText(str(self.feedback_text))
        self._update_progress_bar(self.feedback_text)
        self.update()
        QtWidgets.QApplication.processEvents()
        if self.feedback_text > 500:
            self._explodeButton()
        # DO THE OPERATION WITH self.feedback_text

        # End of main operation --------------------------------------------- #
        # =~---------------------------------------------------------------~= #

    def deactivate(self):
        # print "deactivate"
        self.sticky_start = False
        self.is_activated = False
        self.hide()

    def modifier_changed(self):
        # Change css for modifiers
        if not self.is_activated:
            if any(self.modifiers):
                colors = [CTRL_COLOR, ALT_COLOR, SHIFT_COLOR]
                zipped = zip(self.modifiers, colors)
                modifier_color = (0, 0, 0)
                for mod, color in zipped:
                    if mod == 1:
                        added_modifier_color = tuple(map(sum,zip(modifier_color, color)))
                self.active_color = [clamp(x, 0, 255) for x in added_modifier_color]

            else:
                self.active_color = RANGE_COLOR

        self.GE_Draw.repaint()
        self.GE_Draw.update()
        self.Timeline_Draw.repaint()
        self.Timeline_Draw.update()

    def update_timeline_region(self, *args):
        self.Timeline_Draw.frame_times = _get_timeline_range()

    def update_ge_region(self, *args):
        self.GE_Draw.frame_times = _get_timeline_range()


class GE_Overlay(QtWidgets.QWidget):
        def __init__(self, parent):
            self.frame_times = _get_timeline_range()
            self.ge_widget = _get_graphEditor()
            super(GE_Overlay, self).__init__(self.ge_widget)
            self._parent = parent

        def paintEvent(self, paint_event):
            parent = self.parentWidget()
            if parent:
                # ----------------------------------------------------------- #
                # Basic frame geometry stuff
                self.setGeometry(parent.geometry())

                frame_width  = self.ge_widget.frameSize().width()
                frame_height = self.ge_widget.frameSize().height()

                # Get initial frame range of GE panel
                # Taken from the maya docs for MGraphEditorInfo()
                leftSu=om.MScriptUtil(0.0)
                leftPtr=leftSu.asDoublePtr()
                rightSu=om.MScriptUtil(0.0)
                rightPtr=rightSu.asDoublePtr()
                bottomSu=om.MScriptUtil(0.0)
                bottomPtr=bottomSu.asDoublePtr()
                topSu=om.MScriptUtil(0.0)
                topPtr=topSu.asDoublePtr()

                omui.MGraphEditorInfo().getViewportBounds(leftPtr,
                                                          rightPtr,
                                                          bottomPtr,
                                                          topPtr)

                ge_left_frame = om.MScriptUtil(leftPtr).asDouble()
                ge_right_frame = om.MScriptUtil(rightPtr).asDouble()

                # Distance in numbers of frames visible in the widget
                total_visible_frames = ge_right_frame - ge_left_frame # It floats!

                # ----------------------------------------------------------- #
                # Painter widgets
                painter = QtGui.QPainter(self)
                fill_color = QtGui.QColor(*self._parent.active_color)
                fill_color.setAlpha(ALPHA)

                pen = painter.pen()
                pen.setWidth(1)
                highlight_color = [clamp(x + 10, 0, 255) for x in self._parent.active_color]
                pen_color = QtGui.QColor(*highlight_color)
                pen_color.setAlpha(clamp(ALPHA * 2, 0, 255))
                pen.setColor(pen_color)
                painter.setPen(pen)

                for frame_group in list(group(self.frame_times)):
                    # Start frame calculated against the width of the frame
                    ratio_left_side = (frame_group[0] - ge_left_frame)\
                                       / total_visible_frames
                    left_side_geometry = ratio_left_side * frame_width

                    # End frame calculated against the width of the frame
                    ratio_right_side = (frame_group[-1] - ge_left_frame + 1)\
                                        / total_visible_frames
                    right_side_geometry = ratio_right_side * frame_width

                    painter.fillRect(left_side_geometry,
                                     1, # From the top
                                     right_side_geometry-left_side_geometry,
                                     frame_height-1, # To the bottom
                                     fill_color)
                    painter.drawRect(left_side_geometry,
                                     1, # Watch out for stroke thickness
                                     right_side_geometry-left_side_geometry,
                                     frame_height-2)


class Timeline_Overlay(QtWidgets.QWidget):
    def __init__(self, parent):
        # self.time_control = _get_time_control()
        self.time_control_widget = _get_time_widget()
        self.frame_times = _get_timeline_range()
        super(Timeline_Overlay, self).__init__(self.time_control_widget)
        self._parent = parent

    def paintEvent(self, paint_event):
        parent = self.parentWidget()
        if parent:
            # --------------------------------------------------------------- #
            # Basic frame geometry stuff
            self.setGeometry(parent.geometry())

            range_start = cmds.playbackOptions(query=True, minTime=True)
            range_end   = cmds.playbackOptions(query=True, maxTime=True)
            displayed_frame_count = range_end - range_start + 1

            height = self.parent().height()
            padding = self.width() * 0.005
            frame_width = (self.width() * 0.99) / displayed_frame_count

            # --------------------------------------------------------------- #
            # Painter widgets
            painter = QtGui.QPainter(self)
            fill_color = QtGui.QColor(*self._parent.active_color)
            fill_color.setAlpha(ALPHA)

            pen = painter.pen()
            pen.setWidth(1)
            highlight_color = [clamp(x + 10, 0, 255) for x in self._parent.active_color]
            pen_color = QtGui.QColor(*highlight_color)
            pen_color.setAlpha(clamp(ALPHA * 2, 0, 255))
            pen.setColor(pen_color)
            painter.setPen(pen)

            # --------------------------------------------------------------- #
            # Can support individual frames with groups, etc..
            for frame_group in list(group(self.frame_times)):

                range_frame_times = max(frame_group) - min(frame_group) + 1
                start_frame = frame_group[0]
                start_width = frame_width * (start_frame-range_start) + 1
                end_width = frame_width * range_frame_times

                painter.fillRect(padding + start_width,
                                 0,
                                 end_width-2,
                                 height,
                                 fill_color)
                painter.drawRect(padding + start_width,
                                 1, # Watch out for stroke thickness
                                 end_width-2,
                                 height-2)



# =~-----------------------------------------------------------------------~= #
# =~-/ Developer section

if __name__ == "__main__": # For coding within Maya.
    try:
        InterfaceTest01.close() # pylint:disable=E0601
        InterfaceTest01.deleteLater() # pylint:disable=E0601
    except: pass

    InterfaceTest01 = Interface_Test()
    # InterfaceTest01.show()

