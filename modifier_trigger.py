import maya.OpenMayaUI as omui
from maya import cmds, mel

from Qt import QtCore, QtWidgets, QtGui, QtCompat # pylint:disable=E0611

def _getMainMayaWindow():
    mayaMainWindowPtr = omui.MQtUtil.mainWindow()
    mayaMainWindow = QtCompat.wrapInstance(long(mayaMainWindowPtr), QtWidgets.QWidget)
    return mayaMainWindow

class Test(QtWidgets.QDialog): # Could be anything, really.
    def __init__(self, parent=_getMainMayaWindow()):
        super(Test, self).__init__(parent)
        self._parent = self.parent()
        self.BTN_main = QtWidgets.QPushButton()
        self.BTN_main.setFixedSize(100,100)
        self.setFixedSize(100, 100)
        self.modifiers = set([])

    def showEvent(self, event):
        QtWidgets.QApplication.instance().installEventFilter(self)

    def closeEvent(self, event):
        QtWidgets.QApplication.instance().removeEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Alt and 'alt' not in self.modifiers:
                self.modifiers.add('alt')
                self.process_modifiers()
                return False
            if event.key() == QtCore.Qt.Key_Control and 'ctrl' not in self.modifiers:
                self.modifiers.add('ctrl')
                self.process_modifiers()
                return False
            if event.key() == QtCore.Qt.Key_Shift and 'shift' not in self.modifiers:
                self.modifiers.add('shift')
                self.process_modifiers()
                return False

        if event.type() == QtCore.QEvent.KeyRelease:
            if event.key() == QtCore.Qt.Key_Alt and 'alt' in self.modifiers:
                self.modifiers.discard('alt')
                self.process_modifiers()
                return False
            if event.key() == QtCore.Qt.Key_Control and 'ctrl' in self.modifiers:
                self.modifiers.discard('ctrl')
                self.process_modifiers()
                return False
            if event.key() == QtCore.Qt.Key_Shift and 'shift' in self.modifiers:
                self.modifiers.discard('shift')
                self.process_modifiers()
                return False

        return QtCore.QObject.eventFilter(self, obj, event)

    def process_modifiers(self):
        if not self.modifiers:
            print "No mods!"
        else:
            print self.modifiers

if __name__ == '__main__':
    try:
        test.close() # pylint:disable=E0601
        test.deleteLater()
    except: pass

    test = Test()
    test.show()
