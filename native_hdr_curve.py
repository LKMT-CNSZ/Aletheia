"""Monotone curve in log2(1 + linear RGB peak), black through +6 EV."""
import numpy as np
from PySide6.QtCore import QRectF,QPointF
from PySide6.QtGui import QPainter,QPen,QColor
from native_widgets import CurveEditor
from i18n import tr as _t,ui as _ui

class HDRCurveEditor(CurveEditor):
    def __init__(self):
        super().__init__();self.setMinimumHeight(220)
        _ui(self.setAccessibleName,_t('HDR 扩展曲线：横轴输入，纵轴输出，白点以上按 EV 标注'))
    def area(self):return QRectF(26,14,max(1,self.width()-44),max(1,self.height()-55))
    def paintEvent(self,event):
        super().paintEvent(event)
        p=QPainter(self);r=self.area()
        for ev in (0,1,2,3,4,6):
            u=float(np.log2(1+2.**ev)/np.log2(65.));x=r.left()+u*r.width();y=r.bottom()-u*r.height()
            p.setPen(QPen(QColor('#C77D4A' if ev==0 else '#484848'),1))
            p.drawLine(QPointF(x,r.top()),QPointF(x,r.bottom()));p.drawLine(QPointF(r.left(),y),QPointF(r.right(),y))
            label='W' if ev==0 else '+'+str(ev)
            p.drawText(QRectF(x-11,r.bottom()+3,25,16),label);p.drawText(QRectF(1,y-8,23,16),label)
        p.setPen(QColor('#92918D'));_ui(p.drawText,QRectF(10,self.height()-19,self.width()-20,18),_t('W = SDR 白点 · 曲线在 HDR 限幅前生效'))
