from krita import *
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QSpinBox, QComboBox, QCheckBox
from PyQt5.QtCore import QDir
import math

class SpritesheetExportExtension(Extension):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.exportDialog = UISpritesheetExportDialog()
    
    def setup(self):
        pass
    
    def createActions(self, window):
        actionExport = window.createAction("export_spritesheet", "Export As Spritesheet", "tools/scripts")
        actionExport.triggered.connect(self.onActionExportTriggered)
    
    def onActionExportTriggered(self):
        self.exportDialog.open()

# UI
class UISpritesheetExportDialog(QDialog):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle(i18n("Export As Spritesheet"))
        self.setWindowModality(Qt.NonModal)
        self.setMinimumSize(480, 240)
        
        self.VBox = QVBoxLayout(self)
        
        self.direction = UIDirection()
        self.direction.directionChangedEmitter.directionChanged.connect(self.onDirectionDirectionChanged)
        
        self.layout = UILayout()
        self.anim = UIAnim()
        self.margin = UIMargin()
        self.OkCancel = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.OkCancel.accepted.connect(self.accept)
        self.OkCancel.rejected.connect(self.reject)
        
        direction = self.direction.getDirection()
        self.onDirectionDirectionChanged(direction)
        
        self.VBox.addLayout(self.direction)
        self.VBox.addLayout(self.layout)
        self.VBox.addLayout(self.anim)
        self.VBox.addLayout(self.margin)
        self.VBox.addWidget(self.OkCancel)
    
    def open(self):
        self.direction.open()
        self.layout.open()
        self.anim.open()
        self.margin.open()
        
        self.show()
    
    def exportSpritesheet(self):
        direction = self.direction.getDirection()
        start = self.anim.getRangeStart()
        end = self.anim.getRangeEnd()
        step = self.anim.getRangeStep()
        trim = self.anim.getTrim()
        skipBlank = self.anim.getSkipBlank()
        onlyKeyframes = self.anim.getOnlyKeyframes()
        skipDuplicate = self.anim.getSkipDuplicate()
        margin = self.margin.getMargin()
        
        doc = Krita.instance().activeDocument()
        exportFrameBounds = doc.bounds()
        if trim:
            exportFrameBounds = self.getTrimmedAnimationBounds(start, end, step)
        exportFrameBounds.adjust(margin.left(), margin.top(), margin.right(), margin.bottom())
        exportFrameWidth = exportFrameBounds.width()
        exportFrameHeight = exportFrameBounds.height()
        
        exportDocWidth = -1
        exportDocHeight = -1
        animationFrames = self.getAnimationFrames(start, end, step, skipBlank, onlyKeyframes, skipDuplicate)
        numFrames = len(animationFrames)
        if direction == "Horizontal":
            columns = self.layout.getColumns()
            exportDocWidth = min(columns, numFrames) * exportFrameWidth
            exportDocHeight = int(math.ceil(numFrames / columns)) * exportFrameHeight
            
        elif direction == "Vertical":
            rows = self.layout.getRows()
            exportDocWidth = int(math.ceil(numFrames / rows)) * exportFrameWidth
            exportDocHeight = min(rows, numFrames) * exportFrameHeight
        
        exportDoc = self.createExportDocument(exportDocWidth, exportDocHeight)
        exportRootNode = exportDoc.rootNode()
        exportNode = exportDoc.createNode("Spritesheet", "paintLayer")
        i = 0
        for idx in animationFrames:
            doc.setCurrentTime(idx)
            doc.waitForDone()
            
            exportFrameBoundsLeft = exportFrameBounds.left()
            exportFrameBoundsTop = exportFrameBounds.top() 
            pixelData = doc.pixelData(exportFrameBoundsLeft, exportFrameBoundsTop,
                                      exportFrameWidth, exportFrameHeight)
            
            exportNodeX = -1
            exportNodeY = -1
            if direction == "Horizontal":
                columns = self.layout.getColumns()
                row = i % columns
                exportNodeX = row * exportFrameWidth
                
                column = int(i / columns)
                exportNodeY = column * exportFrameHeight
            
            elif direction == "Vertical":
                rows = self.layout.getRows()
                column = i % rows
                exportNodeY = column * exportFrameHeight
                
                row = int(i / rows)
                exportNodeX = row * exportFrameWidth
            
            exportNode.setPixelData(pixelData, exportNodeX, exportNodeY,
                                    exportFrameWidth, exportFrameHeight)
            
            i += 1
        
        exportRootNode.addChildNode(exportNode, None)
        Krita.instance().activeWindow().addView(exportDoc)
    
    def createExportDocument(self, exportWidth, exportHeight):
        doc = Krita.instance().activeDocument()
        docColorModel = doc.colorModel()
        docColorDepth = doc.colorDepth()
        docColorProfile = doc.colorProfile()
        docResolution = doc.resolution()
        
        doc = Krita.instance().createDocument(exportWidth, exportHeight, "Spritesheet", docColorModel, 
                                              docColorDepth, docColorProfile, docResolution)
        rootNode = doc.rootNode()
        backgroundLayer = rootNode.childNodes()[0]
        backgroundLayer.setVisible(False)
        
        return doc
    
    def getTrimmedAnimationBounds(self, start, end, step):
        doc = Krita.instance().activeDocument()
        docWidth = doc.width()
        docHeight = doc.height()
        rootNode = doc.rootNode()
        
        bounds = QRect()
        bounds.setLeft(docWidth)
        bounds.setTop(docHeight)
        bounds.setRight(0)
        bounds.setBottom(0)
        for i in range(start, end + 1, step):
            doc.setCurrentTime(i)
            doc.waitForDone()
            
            frameBounds = rootNode.bounds()
            if frameBounds.isEmpty():
                continue
            
            bounds.setLeft(min(bounds.left(), frameBounds.left()))
            bounds.setTop(min(bounds.top(), frameBounds.top()))
            bounds.setRight(max(bounds.right(), frameBounds.right()))
            bounds.setBottom(max(bounds.bottom(), frameBounds.bottom()))
        
        return bounds
    
    def getAnimationFrames(self, start, end, step, skipBlank, onlyKeyframes, skipDuplicate):
        doc = Krita.instance().activeDocument()
        rootNode = doc.rootNode()
        prevPixelData = []
        animationFrames = []
        for i in range(start, end + 1, step):
            doc.setCurrentTime(i)
            doc.waitForDone()
            
            if skipBlank:
                frameBounds = rootNode.bounds()
                if frameBounds.isEmpty():
                    continue
            
            if onlyKeyframes:
                hasKeyframe = self.hasNodeKeyframeAtTime(rootNode, i)
                if not hasKeyframe:
                    continue
            
            if skipDuplicate:
                frameBounds = rootNode.bounds()
                pixelData = doc.pixelData(frameBounds.left(), frameBounds.top(),
                                          frameBounds.width(), frameBounds.height())
                isDuplicate = False
                for prev in prevPixelData:
                    if pixelData == prev:
                        isDuplicate = True
                        break
                if isDuplicate:
                    continue
                
                prevPixelData.append(pixelData)
            
            animationFrames.append(i)
        
        return animationFrames
    
    def hasNodeKeyframeAtTime(self, node, idx):
        hasKeyframeAtTime = node.hasKeyframeAtTime(idx)
        if not hasKeyframeAtTime:
            for child in node.childNodes():
                if not child.visible():
                    continue
                if self.hasNodeKeyframeAtTime(child, idx):
                    hasKeyframeAtTime = True
                    break
        
        return hasKeyframeAtTime
    
    def onDirectionDirectionChanged(self, direction):
        if direction == "Horizontal":
            self.layout.setRowsValueEnabled(False)
            self.layout.setColumnsValueEnabled(True)
        elif direction == "Vertical":
            self.layout.setRowsValueEnabled(True)
            self.layout.setColumnsValueEnabled(False)
    
    def accept(self):
        self.exportSpritesheet()
        super().accept()

class UIDirection(QVBoxLayout):
    def __init__(self):
        super().__init__()
        
        self.directionChangedEmitter = self.DirectionChangedEmitter()
        
        self.desc = QLabel("Direction")
        self.value = QComboBox()
        self.value.currentIndexChanged.connect(self.onValueCurrentIndexChanged)
        self.value.addItem("Horizontal")
        self.value.addItem("Vertical")
        
        self.addWidget(self.desc)
        self.addWidget(self.value)
    
    def open(self):
        pass
    
    def getDirection(self):
        return self.value.currentText()
    
    def onValueCurrentIndexChanged(self, idx):
        itemText = self.value.itemText(idx)
        self.directionChangedEmitter.directionChanged.emit(itemText)
    
    class DirectionChangedEmitter(QObject):
        directionChanged = pyqtSignal(str)

class UILayout(QHBoxLayout):
    def __init__(self):
        super().__init__()
        
        self.rows = QVBoxLayout()
        self.rowsDesc = QLabel("Rows")
        self.rowsValue = QSpinBox()
        self.rowsValue.setMinimum(1)
        self.rowsValue.valueChanged.connect(self.onRowsValueValueChanged)
        self.rowsValueChanged = False
        self.rows.addWidget(self.rowsDesc)
        self.rows.addWidget(self.rowsValue)

        self.columns = QVBoxLayout()
        self.columnsDesc = QLabel("Columns")
        self.columnsValue = QSpinBox()
        self.columnsValue.setMinimum(1)
        self.columnsValue.valueChanged.connect(self.onColumnsValueValueChanged)
        self.columnsValueChanged = False
        self.columns.addWidget(self.columnsDesc)
        self.columns.addWidget(self.columnsValue)
        
        self.addLayout(self.rows)
        self.addLayout(self.columns)
    
    def open(self):
        doc = Krita.instance().activeDocument()
        startTime = doc.playBackStartTime()
        endTime = doc.playBackEndTime()
        animLength = (endTime - startTime) + 1
        
        self.rowsValue.setMaximum(animLength)
        self.columnsValue.setMaximum(animLength)
        
        if not self.rowsValueChanged:
            self.rowsValue.blockSignals(True)
            self.rowsValue.setValue(animLength)
            self.rowsValue.blockSignals(False)
        if not self.columnsValueChanged:
            self.columnsValue.blockSignals(True)
            self.columnsValue.setValue(animLength)
            self.columnsValue.blockSignals(False)
    
    def setRowsValueEnabled(self, enabled):
        self.rowsValue.setEnabled(enabled)
    
    def setColumnsValueEnabled(self, enabled):
        self.columnsValue.setEnabled(enabled)
    
    def getRows(self):
        return self.rowsValue.value()
    
    def getColumns(self):
        return self.columnsValue.value()
    
    def onRowsValueValueChanged(self, value):
        self.rowsValueChanged = True
    
    def onColumnsValueValueChanged(self, value):
        self.columnsValueChanged = True

class UIAnim(QVBoxLayout):
    def __init__(self):
        super().__init__()
        
        self.range = QHBoxLayout()
        self.rangeStart = QVBoxLayout()
        self.rangeStartDesc = QLabel("Start")
        self.rangeStartValue = QSpinBox()
        self.rangeStartValue.valueChanged.connect(self.onRangeStartValueValueChanged)
        self.rangeStart.addWidget(self.rangeStartDesc)
        self.rangeStart.addWidget(self.rangeStartValue)
        
        self.rangeEnd = QVBoxLayout()
        self.rangeEndDesc = QLabel("End")
        self.rangeEndValue = QSpinBox()
        self.rangeEndValue.valueChanged.connect(self.onRangeEndValueValueChanged)
        self.rangeEndValueChanged = False
        self.rangeEnd.addWidget(self.rangeEndDesc)
        self.rangeEnd.addWidget(self.rangeEndValue)
        
        self.rangeStep = QVBoxLayout()
        self.rangeStepDesc = QLabel("Step")
        self.rangeStepValue = QSpinBox()
        self.rangeStepValue.setMinimum(1)
        self.rangeStep.addWidget(self.rangeStepDesc)
        self.rangeStep.addWidget(self.rangeStepValue)
        
        self.range.addLayout(self.rangeStart)
        self.range.addLayout(self.rangeEnd)
        self.range.addLayout(self.rangeStep)
        
        self.options = QHBoxLayout()
        self.optionsTrim = QVBoxLayout()
        self.optionsTrimDesc = QLabel("Trim")
        self.optionsTrimValue = QCheckBox()
        self.optionsTrim.addWidget(self.optionsTrimDesc)
        self.optionsTrim.addWidget(self.optionsTrimValue)
        
        self.optionsSkipBlank = QVBoxLayout()
        self.optionsSkipBlankDesc = QLabel("Skip Blank")
        self.optionsSkipBlankValue = QCheckBox()
        self.optionsSkipBlank.addWidget(self.optionsSkipBlankDesc)
        self.optionsSkipBlank.addWidget(self.optionsSkipBlankValue)
        
        self.optionsOnlyKeyframes = QVBoxLayout()
        self.optionsOnlyKeyframesDesc = QLabel("Only Keyframes")
        self.optionsOnlyKeyframesValue = QCheckBox()
        self.optionsOnlyKeyframes.addWidget(self.optionsOnlyKeyframesDesc)
        self.optionsOnlyKeyframes.addWidget(self.optionsOnlyKeyframesValue)
        
        self.optionsSkipDuplicate = QVBoxLayout()
        self.optionsSkipDuplicateDesc = QLabel("Skip Duplicate")
        self.optionsSkipDuplicateValue = QCheckBox()
        self.optionsSkipDuplicate.addWidget(self.optionsSkipDuplicateDesc)
        self.optionsSkipDuplicate.addWidget(self.optionsSkipDuplicateValue)
        
        self.options.addLayout(self.optionsTrim)
        self.options.addLayout(self.optionsSkipBlank)
        self.options.addLayout(self.optionsOnlyKeyframes)
        self.options.addLayout(self.optionsSkipDuplicate)
        
        self.addLayout(self.range)
        self.addLayout(self.options)
    
    def open(self):
        doc = Krita.instance().activeDocument()
        startTime = doc.playBackStartTime()
        endTime = doc.playBackEndTime()
        
        self.rangeStartValue.setMinimum(startTime)
        self.rangeEndValue.setMinimum(startTime)
        
        self.rangeStartValue.setMaximum(endTime)
        self.rangeEndValue.setMaximum(endTime)
        self.rangeStepValue.setMaximum(endTime)
        
        if not self.rangeEndValueChanged:
            self.rangeEndValue.blockSignals(True)
            self.rangeEndValue.setValue(endTime)
            self.rangeEndValue.blockSignals(False)
    
    def getRangeStart(self):
        return self.rangeStartValue.value()
    
    def getRangeEnd(self):
        return self.rangeEndValue.value()
    
    def getRangeStep(self):
        return self.rangeStepValue.value()
    
    def getTrim(self):
        return self.optionsTrimValue.isChecked()
    
    def getSkipBlank(self):
        return self.optionsSkipBlankValue.isChecked()
    
    def getOnlyKeyframes(self):
        return self.optionsOnlyKeyframesValue.isChecked()
    
    def getSkipDuplicate(self):
        return self.optionsSkipDuplicateValue.isChecked()
    
    def onRangeStartValueValueChanged(self, value):
        endValue = self.rangeEndValue.value()
        if endValue < value:
            self.rangeEndValue.setValue(value)
            endValue = value
        
        self.rangeStepValue.setMaximum(max(endValue - value, 1))
    
    def onRangeEndValueValueChanged(self, value):
        startValue = self.rangeStartValue.value()
        if startValue > value:
            self.rangeStartValue.setValue(value)
            startValue = value
        
        self.rangeStepValue.setMaximum(max(value - startValue, 1))
        
        self.rangeEndValueChanged = True

class UIMargin(QVBoxLayout):
    def __init__(self):
        super().__init__()
        
        self.desc = QLabel("Margin")
        self.HBox = QHBoxLayout()
        
        self.left = QVBoxLayout()
        self.leftDesc = QLabel("Left")
        self.leftValue = QSpinBox()
        self.leftValue.setMinimum(-999)
        self.leftValue.setMaximum(999)
        self.left.addWidget(self.leftDesc)
        self.left.addWidget(self.leftValue)
        
        self.top = QVBoxLayout()
        self.topDesc = QLabel("Top")
        self.topValue = QSpinBox()
        self.topValue.setMinimum(-999)
        self.topValue.setMaximum(999)
        self.top.addWidget(self.topDesc)
        self.top.addWidget(self.topValue)
        
        self.right = QVBoxLayout()
        self.rightDesc = QLabel("Right")
        self.rightValue = QSpinBox()
        self.rightValue.setMinimum(-999)
        self.rightValue.setMaximum(999)
        self.right.addWidget(self.rightDesc)
        self.right.addWidget(self.rightValue)
        
        self.bottom = QVBoxLayout()
        self.bottomDesc = QLabel("Bottom")
        self.bottomValue = QSpinBox()
        self.bottomValue.setMinimum(-999)
        self.bottomValue.setMaximum(999)
        self.bottom.addWidget(self.bottomDesc)
        self.bottom.addWidget(self.bottomValue)
        
        self.HBox.addLayout(self.left)
        self.HBox.addLayout(self.top)
        self.HBox.addLayout(self.right)
        self.HBox.addLayout(self.bottom)
        
        self.addWidget(self.desc)
        self.addLayout(self.HBox)
    
    def open(self):
        pass
    
    def getMargin(self):
        left = self.leftValue.value()
        top = self.topValue.value()
        right = self.rightValue.value()
        bottom = self.bottomValue.value()
        margin = QRect()
        margin.setLeft(-left)
        margin.setTop(-top)
        margin.setRight(right)
        margin.setBottom(bottom)
        
        return margin

Krita.instance().addExtension(SpritesheetExportExtension(Krita.instance()))