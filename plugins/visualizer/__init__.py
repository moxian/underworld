import gameengine
import threading
from PyQt4 import QtGui, QtCore
from PyQt4.Qt import Qt
import copy
import time
import sys
import argparse

minZoomExp = -20.
maxZoomExp = 10.
defaultZoom = -5.

cellSize = 64
hBarBorder = 6
hBarHeight = 6

def bound(minVal, current, maxVal):
    return max(min(current, maxVal), minVal)

class VisualizerWidget(QtGui.QWidget):
    PlayerColors = [ QtGui.QColor(255, 0, 0), QtGui.QColor(0, 0, 255),
                     QtGui.QColor(0, 200, 0), QtGui.QColor(180, 160, 0) ]
    NeutralColor = QtGui.QColor(0, 0, 0)
    def __init__(self, parent, visualizer):
        super(VisualizerWidget, self).__init__(parent)
        self._visualizer = visualizer
        self.zoomExp = defaultZoom
        self.shift = QtCore.QPointF(0., 0.)
        self.isDragging = False
    def zoomFactor(zoomExp):
        return pow(1.1, zoomExp)
    def currentTransform(self):
        zoom = VisualizerWidget.zoomFactor(self.zoomExp)
        return QtGui.QTransform(zoom, 0., 0., zoom, self.shift.x(), self.shift.y())
    def paintEvent(self, event):
        objects = self._visualizer.objects
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHints(  QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing
                               | QtGui.QPainter.SmoothPixmapTransform | QtGui.QPainter.HighQualityAntialiasing)
        painter.fillRect(self.rect(), QtGui.QColor.fromRgbF(0.5, 0.5, 0.5))
        painter.setTransform(self.currentTransform())
        painter.setFont(QtGui.QFont('', cellSize / 2))
        worldRect = QtCore.QRectF(0., 0., self._visualizer.game.SizeX * cellSize, self._visualizer.game.SizeY * cellSize)
        #backgroundBrush = QtGui.QBrush(QtGui.QPixmap('graphics/dirt.jpg'))
        #backgroundBrush.setTransform(QtGui.QTransform.fromScale(0.3, 0.3))
        backgroundBrush = QtGui.QBrush(QtGui.QColor.fromRgbF(0.9, 0.9, 0.9))
        painter.fillRect(worldRect, backgroundBrush)
        for o in objects:
            if o.owner >= 0:
                mainColor = self.PlayerColors[o.owner]
            else:
                mainColor = self.NeutralColor
            cellRect = QtCore.QRectF(o.x * cellSize, o.y * cellSize, cellSize, cellSize)
            textRect = copy.copy(cellRect)
            if isinstance(o, gameengine.Game.Building):
                pen = QtGui.QPen(mainColor)
                pen.setWidth(1)
                painter.setPen(pen)
                fillColor = copy.copy(mainColor)
                fillColor.setHsvF(fillColor.hueF(), fillColor.saturationF() * 0.5, fillColor.valueF(), 0.2)
                painter.setBrush(fillColor)
                buildingRect = cellRect.adjusted(0.5, 0.5, -0.5, -0.5)
                painter.drawRect(buildingRect)
            if o.TakesDamage:
                hBarRect = cellRect.adjusted(hBarBorder, hBarBorder, -hBarBorder, -hBarBorder)
                hBarRect.setHeight(hBarHeight)
                hBarGreenRect = copy.copy(hBarRect)
                hBarGreenRect.setWidth(hBarRect.width() * o.hitpoints / o.MaxHitpoints)
                pen = QtGui.QPen(QtGui.QColor(QtCore.Qt.black))
                pen.setWidth(1)
                painter.setPen(pen)
                painter.setBrush(QtGui.QBrush(QtGui.QColor(QtCore.Qt.red)))
                painter.drawRect(hBarRect)
                painter.setBrush(QtGui.QBrush(QtGui.QColor(QtCore.Qt.green)))
                painter.drawRect(hBarGreenRect)
                textRect.setTop(hBarRect.bottom())
            painter.setPen(mainColor.darker(125))
            painter.drawText(textRect, QtCore.Qt.AlignCenter, o.CharRepr)
        painter.end()
    def wheelEvent(self, event):
        oldZoom = VisualizerWidget.zoomFactor(self.zoomExp)
        self.zoomExp += event.delta() / 120.
        self.zoomExp = bound(minZoomExp, self.zoomExp, maxZoomExp)
        newZoom = VisualizerWidget.zoomFactor(self.zoomExp)
        self.shift += (event.pos() - self.shift) * (1. - newZoom / oldZoom)
        self.update()
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.isDragging = True
            self.dragStart = event.pos()
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.isDragging = False
    def mouseMoveEvent(self, event):
        if self.isDragging:
            self.shift += event.pos() - self.dragStart
            self.dragStart = event.pos()
            self.update()

class PlayerStatTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent, visualizer):
        super(PlayerStatTableModel, self).__init__(parent)
        self._visualizer = visualizer
        self._players = self._visualizer.game.players
        self._playersData = [p.getPlayerStats() for p in self._players]
        self._attributeNames = [t[0] for t in self._players[0].getPlayerStats( )]

    def columnCount(self, parent = QtCore.QModelIndex()):
        return len(self._players)
    def headerData(self, section, orientation, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return "[%d] %s" % (section, self._players[section].name)
            else:
                return self._attributeNames[section]
        return None
    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self._playersData[index.column( )][index.row( )][1]
        return None
    def rowCount(self, parent = QtCore.QModelIndex()):
        return len(self._attributeNames)
    def endTurn(self):
        self._playersData = [p.getPlayerStats() for p in self._players]
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

class MainWidget(QtGui.QWidget):
    turnEnded = QtCore.pyqtSignal()
    def __init__(self, visualizer):
        super( ).__init__( )
        playerStatTableModel = PlayerStatTableModel(self, visualizer)
        playerStatTableView = QtGui.QTableView(self)
        playerStatTableView.setModel(playerStatTableModel)
        self.turnEnded.connect(playerStatTableModel.endTurn)
        visualizerWidget = VisualizerWidget(self, visualizer)
        visualizerWidget.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.layout = QtGui.QHBoxLayout()
        self.layout.setMargin(0)
        self.layout.addWidget(visualizerWidget)
        self.layout.addWidget(playerStatTableView)
        self.layout.setStretch(0, 2)
        self.layout.setStretch(1, 1)
        self.setLayout(self.layout)
        self.setGeometry(120, 120, 800, 600)
        self.setWindowTitle('Underworld')
        self.show()
    def event(self, ev):
        if ev.type( ) == QtCore.QEvent.User + 1:
            self.update( )
            self.turnEnded.emit()
        return super(MainWidget, self).event(ev)

class VisualizerClosedException( Exception ):
    pass

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage( )
        sys.stderr.write("replay plugin error: " + message + "\n")
        sys.exit(2)

class Plugin:
    def __init__(self, game, args):
        """
            Initialize a visualizer with an instance of Game.
            sets onTurnEnd binding, spawns a GUI thread
        """
        parser = ArgumentParser(prog="")
        parser.add_argument("--turn-time", "-t", 
                            type=float, 
                            help="delay between turns in seconds(%(default)f)",
                            default=0.1)
        self._options = parser.parse_args(args.split( ))
        self._readyEvent = threading.Event( )
        self.game = game
        self.objects = copy.deepcopy(self.game.objects)
        self._thread = threading.Thread(target=self._mainLoop)
        self._thread.start( )
        self._readyEvent.wait( )

    def _turnEnd(self):
        """
            The event handler. Abuses the fact that assignment is atomic
        """
        self.objects = copy.deepcopy(self.game.objects)
        self._app.postEvent(self._widget, QtCore.QEvent(QtCore.QEvent.User + 1))
        time.sleep(self._options.turn_time)
        if not self._thread.is_alive():
            raise VisualizerClosedException()

    def _mainLoop(self):
        """
            GUI main loop - a separate thread
        """
        self._app = QtGui.QApplication([])
        self._widget = MainWidget(self)
        self.game.register_turn_end_handler(self._turnEnd)
        self._readyEvent.set( )
        self._app.exec_()

__all__ = ["Visualizer"]
