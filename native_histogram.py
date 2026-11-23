"""Compact RGB density plot with a shared SDR/HDR graph and range strip."""
import math
import numpy as np
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QColor,QPainter,QPen,QPainterPath,QPolygonF
from PySide6.QtWidgets import QWidget,QMenu,QToolTip
from i18n import tr as _t,trf as _tf,ui as _ui

COLORS=('#e13e39','#4ec24d','#367bd3')

class Histogram(QWidget):
    def __init__(self):
        super().__init__();self.bins=None;self.hdr_data=None;self.hdr_enabled=False;self.headroom=None;self.log_scale=False
        self.setMinimumHeight(136);self.setMaximumHeight(166);self.setMouseTracking(True)
        _ui(self.setAccessibleName,_t('RGB 直方图'))
    def set_bins(self,bins):self.bins=bins;self.update()
    def set_hdr_bins(self,data,enabled=False,headroom=None):
        self.hdr_enabled=bool(enabled);self.hdr_data=data if enabled else None
        self.headroom=float(headroom) if headroom is not None and np.isfinite(headroom) else None
        self.setMinimumHeight(156 if enabled else 136);self.setMaximumHeight(180 if enabled else 166)
        _ui(self.setAccessibleName,_t('SDR / HDR 分区 RGB 直方图') if enabled else _t('RGB 直方图'))
        _ui(self.setToolTip,_t('RGB 彩色叠加直方图。开启 HDR 后，左侧为 SDR，右侧为参考白以上的 HDR，横轴按 EV 分档。底部浅色条标出屏幕可用范围。点击标题或右键切换纵轴；悬停图表查看范围。'))
        self.update()
    def display_stops(self):
        peak=(self.hdr_data or {}).get('peak_ev') or 0
        return max(4,min(6,int(math.ceil(max(peak,self.headroom or 0)))))
    def chart(self):return QRectF(12,29,max(1,self.width()-24),max(1,self.height()-62))
    def curves(self):
        from hdr_histogram import SDR_BINS,HDR_BINS,HDR_STOPS,SDR_SHARE
        if self.hdr_enabled:
            data=self.hdr_data
            if data is None:return None,None
            stops=self.display_stops();n=round(HDR_BINS*stops/HDR_STOPS)
            xs=np.concatenate(((np.arange(SDR_BINS)+.5)/SDR_BINS*SDR_SHARE,
                               SDR_SHARE+(np.arange(n)+.5)/n*(1-SDR_SHARE)))
            counts=[np.concatenate((b[:SDR_BINS],b[SDR_BINS:SDR_BINS+n])) for b in data['bins']]
        else:
            if self.bins is None:return None,None
            xs=np.linspace(0,1,len(self.bins[0]));counts=self.bins
        # Small symmetric visual smoothing; statistical counts remain unchanged.
        kernel=np.array([1,4,6,4,1],float)/16
        curves=[np.convolve(np.asarray(b,float),kernel,'same') for b in counts]
        if self.log_scale:curves=[np.log1p(b) for b in curves]
        peak=max(1.,max(float(b.max()) for b in curves))
        return xs,[b/peak for b in curves]
    def paintEvent(self,event):
        from hdr_histogram import SDR_SHARE
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor('#202020'))
        p.setPen(QColor('#bcbab5'))
        _ui(p.drawText,QRectF(12,2,self.width()-38,23),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,_t('直方图'))
        x=self.width()-17;p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#bcbab5'))
        p.drawPolygon(QPolygonF([QPointF(x-4,11),QPointF(x+4,11),QPointF(x,16)]));p.setBrush(Qt.BrushStyle.NoBrush)
        box=self.chart();split=box.left()+box.width()*SDR_SHARE
        p.fillRect(box,QColor('#242424'));p.setPen(QPen(QColor('#383838'),1))
        if self.hdr_enabled:
            for fraction in (.25,.5,.75):
                x=box.left()+box.width()*SDR_SHARE*fraction;p.drawLine(QPointF(x,box.top()),QPointF(x,box.bottom()))
            for stop in range(1,self.display_stops()+1):
                x=split+(1-SDR_SHARE)*box.width()*stop/self.display_stops();p.drawLine(QPointF(x,box.top()),QPointF(x,box.bottom()))
        else:
            for fraction in (.25,.5,.75):
                x=box.left()+box.width()*fraction;p.drawLine(QPointF(x,box.top()),QPointF(x,box.bottom()))
        xs,curves=self.curves()
        if curves is not None:
            p.save();p.setClipRect(box)
            paths=[]
            for values in curves:
                path=QPainterPath(QPointF(box.left(),box.bottom()))
                for x,y in zip(xs,values):path.lineTo(QPointF(box.left()+float(x)*box.width(),box.bottom()-float(y)*(box.height()-5)))
                path.lineTo(box.bottomRight());path.closeSubpath();paths.append(path)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            for path,color in zip(paths,COLORS):
                fill=QColor(color);fill.setAlpha(112);p.fillPath(path,fill)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            for path,color in zip(paths,COLORS):p.setPen(QPen(QColor(color),1.3));p.drawPath(path)
            p.restore()
        else:
            p.setPen(QColor('#92918D'));_ui(p.drawText,box,Qt.AlignmentFlag.AlignCenter,_t('正在计算直方图…') if self.hdr_enabled else _t('打开图像后显示 RGB 直方图'))
        # Quiet white divider and segmented capability strip, without a red plot panel.
        p.setPen(QPen(QColor('#111111'),1));p.drawRect(box)
        if self.hdr_enabled:
            p.setPen(QPen(QColor('#797979'),1));p.drawLine(QPointF(split,box.top()),QPointF(split,box.bottom()))
        p.fillRect(QRectF(box.left(),box.bottom()+3,box.width(),5),QColor('#424b45'))
        p.fillRect(QRectF(box.left(),box.bottom()+3,box.width()*(SDR_SHARE if self.hdr_enabled else 1),5),QColor('#deded9'))
        if self.hdr_enabled:
            span=box.width()*(1-SDR_SHARE);stops=self.display_stops()
            if self.headroom is not None:
                length=span*np.clip(self.headroom/stops,0,1)
                p.fillRect(QRectF(split,box.bottom()+3,length,5),QColor('#d9e5d7'))
            p.setPen(QPen(QColor('#202020'),2))
            for stop in range(stops+1):
                x=split+span*stop/stops;p.drawLine(QPointF(x,box.bottom()+2),QPointF(x,box.bottom()+9))
            p.setPen(QColor('#d6d4cf'))
            p.drawText(QRectF(box.left(),box.bottom()+11,box.width()*SDR_SHARE,18),Qt.AlignmentFlag.AlignCenter,'SDR')
            p.drawText(QRectF(split,box.bottom()+11,span,18),Qt.AlignmentFlag.AlignCenter,'HDR')
        else:
            p.setPen(QColor('#92918D'));rect=QRectF(box.left(),box.bottom()+11,box.width(),18)
            p.drawText(rect,Qt.AlignmentFlag.AlignLeft,'0');p.drawText(rect,Qt.AlignmentFlag.AlignRight,'255')
            _ui(p.drawText,rect,Qt.AlignmentFlag.AlignCenter,_t('对数纵轴') if self.log_scale else _t('线性纵轴'))
        # Endpoint flags and information glyph describe genuine data / display limits.
        data=self.hdr_data or {};beyond=self.headroom is not None and (data.get('peak_ev') or 0)>self.headroom
        low=bool(data.get('black_fraction',0)) if self.hdr_enabled else bool(self.bins is not None and any(b[0] for b in self.bins))
        high=beyond or bool(data.get('overflow_fraction',0)) if self.hdr_enabled else bool(self.bins is not None and any(b[-1] for b in self.bins))
        for x,on,color in ((box.left()+10,low,'#8eb1df'),(box.right()-10,high,'#ebbc67')):
            p.setPen(QPen(QColor('#101010'),1));p.setBrush(QColor(color if on else '#161616'))
            p.drawPolygon(QPolygonF([QPointF(x-6,box.top()+12),QPointF(x+6,box.top()+12),QPointF(x,box.top()+3)]))
        if self.hdr_enabled:
            p.setPen(QColor('#aaaaa5'));p.setBrush(Qt.BrushStyle.NoBrush)
            center=QPointF(box.right()-5,box.bottom()+20);p.drawEllipse(center,6,6)
            p.drawText(QRectF(center.x()-5,center.y()-8,10,16),Qt.AlignmentFlag.AlignCenter,'i')
    def menu(self,point):
        menu=QMenu(self)
        for title,logarithmic in ((_t('线性纵轴'),False),(_t('对数纵轴'),True)):
            action=_ui(menu.addAction,title);action.setCheckable(True);action.setChecked(self.log_scale==logarithmic)
            action.triggered.connect(lambda checked=False,mode=logarithmic:self.set_scale(mode))
        menu.exec(point)
    def set_scale(self,logarithmic):self.log_scale=bool(logarithmic);self.update()
    def contextMenuEvent(self,event):self.menu(event.globalPos())
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and event.position().y()<27:self.menu(event.globalPosition().toPoint());return
        if self.hdr_enabled and event.position().y()>self.chart().bottom():
            data=self.hdr_data or {};text=_tf('HDR 范围 +0 至 +{0} EV · HDR 像素 {1:.1f}%',self.display_stops(),data.get('hdr_fraction',0)*100)
            text+=_t('\n当前为 SDR 显示') if self.headroom is None else _tf('\n屏幕余量 +{0:.1f} EV',self.headroom)
            QToolTip.showText(event.globalPosition().toPoint(),str(text),self);return
        super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        from hdr_histogram import SDR_SHARE
        box=self.chart()
        if not box.contains(event.position()):super().mouseMoveEvent(event);return
        u=np.clip((event.position().x()-box.left())/box.width(),0,1)
        if self.hdr_enabled:
            text=_tf('SDR · {0:.0f}%',u/SDR_SHARE*100) if u<=SDR_SHARE else _tf('HDR · +{0:.2f} EV',(u-SDR_SHARE)/(1-SDR_SHARE)*self.display_stops())
        else:text=_tf('SDR · {0:.0f}',u*255)
        QToolTip.showText(event.globalPosition().toPoint(),str(text),self)
