import _thread
import time
import json

def swap(a, b):
    temp = a
    a = b
    b = temp
    return a, b

class SSD1306:

    LCD_WIDTH = 128
    LCD_HEIGHT = 64
    FB_SIZE = int(LCD_WIDTH * LCD_HEIGHT / 8)
    DEFAULT_SPACE = 5

    CMD_SET_CONTRAST = 0x81
    CMD_DISPLAY_ALLON_RESUME = 0xA4
    CMD_DISPLAY_ALLON = 0xA5
    CMD_NORMAL_DISPLAY = 0xA6
    CMD_INVERT_DISPLAY = 0xA7
    CMD_DISPLAY_OFF = 0xAE
    CMD_DISPLAY_ON = 0xAF
    CMD_SET_DISPLAY_OFFSET = 0xD3
    CMD_SET_COMPINS = 0xDA
    CMD_SET_VCOM_DETECT = 0xDB
    CMD_SET_DISPLAY_CLOCKDIV = 0xD5
    CMD_SET_PRECHARGE = 0xD9
    CMD_SET_MULTIPLEX = 0xA8
    CMD_SET_LOW_COLUMN = 0x00
    CMD_SET_HIGH_COLUMN = 0x10
    CMD_SET_START_LINE = 0x40
    CMD_MEMORY_MODE = 0x20
    CMD_COM_SCAN_INC = 0xC0
    CMD_COM_SCAN_DEC = 0xC8
    CMD_SEG_REMAP = 0xA0
    CMD_CHARGE_PUMP = 0x8D
    CMD_CHARGE_PUMP_ON = 0x14
    CMD_CHARGE_PUMP_OFF = 0x10
    CMD_ACTIVATE_SCROLL = 0x2F
    CMD_DEACTIVATE_SCROLL = 0x2E
    CMD_SET_VERTICAL_SCROLL_AREA = 0xA3
    CMD_RIGHT_HORIZONTAL_SCROLL = 0x26
    CMD_LEFT_HORIZONTAL_SCROLL = 0x27
    CMD_VERTICAL_AND_RIGHT_HORIZONTAL_SCROLL = 0x29
    CMD_VERTICAL_AND_LEFT_HORIZONTAL_SCROLL = 0x2A
    
    CONTROL_COMMAND = 0x00
    CONTROL_DATA = 0x40

    OPERATION_XOR = 1
    OPERATION_OR  = 2
    OPERATION_AND = 3
    OPERATION_NOT = 4
    OPERATION_ALL = 5
    
    def _send_command(self, cmd):
        cmd_buff = [self.CONTROL_COMMAND]
        cmd_buff.append(cmd)
              
        self._i2c_bus.writeto(self._addr, bytes(cmd_buff))
        
    
    def _send_data(self, data):
        data_buff = [self.CONTROL_DATA]
        data_buff.extend(data)

        self._i2c_bus.writeto(self._addr, bytes(data_buff))

    def _fb_update(self):
        print(f"Run thread #{_thread.get_ident()} - _fb_update")
        while True:
            if self._need_update:
                with self.fb_lock:
                    self._send_data(self._fb)
                    self._need_update = False

            time.sleep_ms(40)

    def _fb_set_data(self, operation, addr, data, len):
        for idx in range(len):
            if operation == self.OPERATION_XOR:
                self._fb[addr + idx] ^= data
            elif operation == self.OPERATION_OR:
                self._fb[addr + idx] |= data
            elif operation == self.OPERATION_AND:
                self._fb[addr + idx] &= data
            elif operation == self.OPERATION_NOT:
                self._fb[addr + idx] &= ~data
            elif operation == self.OPERATION_ALL:
                self._fb[addr + idx] = data

    def _fb_set_byte(self, operation, addr, data):
        if operation == self.OPERATION_XOR:
            self._fb[addr] ^= data
        elif operation == self.OPERATION_OR:
            self._fb[addr] |= data
        elif operation == self.OPERATION_AND:
            self._fb[addr] &= data
        elif operation == self.OPERATION_NOT:
            self._fb[addr] &= ~data
        elif operation == self.OPERATION_ALL:
            self._fb[addr] = data

    def _fb_set_pixel(self, x, y, operation):
        addr = (y >> 3) * self.LCD_WIDTH + x
        self._fb_set_byte(operation, addr, 1 << int(y & 0x07))

    def _fb_draw_line(self, x0, y0, x1, y1, operation):        
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        step = dy > dx

        if(step):
            x0, y0 = swap(x0, y0)
            x1, y1 = swap(x1, y1)
            dx, dy = swap(dx, dy)
        
        if(x0 > x1):
            x0, x1 = swap(x0, x1)
            y0, y1 = swap(y0, y1)

        y_step = 1 if y0 < y1 else -1
        err = dx >> 1

        while (x0 <= x1):
            if(step):
                self._fb_set_pixel(y0, x0, operation)
            else:
                self._fb_set_pixel(x0, y0, operation)
            err -= dy

            if(err < 0):
                y0 += y_step
                err += dx
            
            x0 += 1

    def _fb_fill_rectangle(self, x0, y0, x1, y1, operation):
        if x1 < x0:
            x0, x1 = swap(x0, x1)

        if y1 < y0:
            y0, y1 = swap(y0, y1)

        pos_b = (y0 >> 3) * self.LCD_WIDTH + x0
        dy = y1 - y0 + 1
        dx = x1 - x0 + 1
        fill_b = (0xFF << (y0 & 0x07) & 0xFF)

        while dy > 0 and pos_b < self.FB_SIZE:
            self._fb_set_data(operation, pos_b, fill_b, dx)
            pos_b += self.LCD_WIDTH
            dy -= 8 - (y0 & 0x07) if fill_b < 0xFF else 8
            fill_b = 0xFF if dy >= 8 else 0xFF >> (8 - dy)

    def _fb_draw_arc(self, x0, y0, r, s, operation):
        xd = 1 - (r << 1)
        yd = 0
        e = 0
        x = r
        y = 0

        while x >= y:
            if s & 0x01:
                self._fb_set_pixel(x0+x, y0-y, operation)
            if s & 0x02:
                self._fb_set_pixel(x0+y, y0-x, operation)
            if s & 0x04:
                self._fb_set_pixel(x0-y, y0-x, operation)
            if s & 0x08:
                self._fb_set_pixel(x0-x, y0-y, operation)
            if s & 0x10:
                self._fb_set_pixel(x0-x, y0+y, operation)
            if s & 0x20:
                self._fb_set_pixel(x0-y, y0+x, operation)
            if s & 0x40:
                self._fb_set_pixel(x0+y, y0+x, operation)
            if s & 0x80:
                self._fb_set_pixel(x0+x, y0+y, operation)

            y += 1
            e += yd
            yd += 2
            if (e << 1) + xd > 0:
                x -= 1
                e += xd
                xd +=2

    def _check_x(self, x):
        if x < 0:
            x = 0
        if x >= self.LCD_WIDTH:
            x = self.LCD_WIDTH - 1
        return x
    
    def _check_y(self, y):
        if y < 0:
            y = 0
        if y >= self.LCD_HEIGHT:
            y = self.LCD_HEIGHT - 1
        return y
    
    def _check_radius(self, x, y, r):
        if r > x or r > y:
            return False
        if r+x >= self.LCD_WIDTH or r+y >= self.LCD_HEIGHT:
            return False
        return True

    def _fb_put_char(self, char, x0, y0, operation):
        char_array = bytes([int(val) for val in self._font.get(char)])
        bytes_per_line = len(self._font.get(char)) / self._font_hight

        byte_idx = 0
        bit_idx = 0
        x = x0;

        for byte in char_array:
            if byte_idx >= bytes_per_line:
                byte_idx = 0
                x = x0;
                bit_idx = 0
                y0 += 1
            
            for bit in range(8):
                if byte & 0x01:
                    self._fb_set_pixel(x, y0, operation)
                byte >>= 1
                x += 1
                bit_idx += 1
                if bit_idx >= self._font_width:
                    break

            byte_idx += 1
        
        return x
	
    def __init__(self, i2c_bus, addr):
        self._i2c_bus = i2c_bus
        self._addr = addr
        self._need_update = True
        self._font_width = 0
        self._font_hight = 0
        self._font = None
        
        devices = self._i2c_bus.scan()
        if not devices or self._addr not in devices:
            print (f"ERROR: there is not device with address {self._addr} on the bus")
            return None

        self._fb = bytearray(self.FB_SIZE)
        self.fb_lock = _thread.allocate_lock()
        
        self._send_command(self.CMD_DISPLAY_OFF)
        self._send_command(self.CMD_SET_DISPLAY_CLOCKDIV)
        self._send_command(0x80)
        self._send_command(self.CMD_SET_MULTIPLEX)
        self._send_command(0x3F)
        self._send_command(self.CMD_SET_DISPLAY_OFFSET)
        self._send_command(0x00)
        self._send_command(self.CMD_SET_START_LINE | 0x00)
        self._send_command(self.CMD_CHARGE_PUMP)
        self._send_command(self.CMD_CHARGE_PUMP_ON)
        self._send_command(self.CMD_MEMORY_MODE)
        self._send_command(0x00)
        self._send_command(self.CMD_SEG_REMAP | 0x01)
        self._send_command(self.CMD_COM_SCAN_DEC)
        self._send_command(self.CMD_SET_COMPINS)
        self._send_command(0x12)
        self._send_command(self.CMD_SET_CONTRAST)
        self._send_command(0x4F)
        self._send_command(self.CMD_SET_PRECHARGE)
        self._send_command(0xF1)
        self._send_command(self.CMD_SET_VCOM_DETECT)
        self._send_command(0x40)
        self._send_command(self.CMD_DISPLAY_ALLON_RESUME)
        self._send_command(self.CMD_NORMAL_DISPLAY)
        self._send_command(self.CMD_DISPLAY_ON)

        _thread.start_new_thread(self._fb_update, ())

    def clear(self):
        with self.fb_lock:
            self._fb_set_data(self.OPERATION_ALL, 0, 0, self.FB_SIZE)
            self._need_update = True

    def putPixel(self, x, y, operation):
        x = self._check_x(x)
        y = self._check_y(y)

        with self.fb_lock:
            self._fb_set_pixel(x, y, operation)
            self._need_update = True

    def drawLine(self, x0, y0, x1, y1, operation):
        x0 = self._check_x(x0)
        x1 = self._check_x(x1)
        y0 = self._check_y(y0)
        y1 = self._check_y(y1)

        with self.fb_lock:
            self._fb_draw_line(x0, y0, x1, y1, operation)
            self._need_update = True

    def drawRectangle(self, x0, y0, x1, y1, operation):
        x0 = self._check_x(x0)
        x1 = self._check_x(x1)
        y0 = self._check_y(y0)
        y1 = self._check_y(y1)

        with self.fb_lock:
            self._fb_draw_line(x0, y0, x1, y0, operation)
            self._fb_draw_line(x0, y0, x0, y1, operation)
            self._fb_draw_line(x1, y0, x1, y1, operation)
            self._fb_draw_line(x0, y1, x1, y1, operation)
            self._need_update = True

    def fillRectangle(self, x0, y0, x1, y1, operation):
        x0 = self._check_x(x0)
        x1 = self._check_x(x1)
        y0 = self._check_y(y0)
        y1 = self._check_y(y1)

        with self.fb_lock:
            self._fb_fill_rectangle(x0, y0, x1, y1, operation)

            self._need_update = True

    def fillRoundRectangle(self, x0, y0, x1, y1, r, operation):
        x0 = self._check_x(x0)
        x1 = self._check_x(x1)
        y0 = self._check_y(y0)
        y1 = self._check_y(y1)

        if x1 < x0:
            x0, x1 = swap(x0, x1)

        if y1 < y0:
            y0, y1 = swap(y0, y1)

        if r < 0:
            r = 0

        xd = 3 - (r << 1)
        x = 0
        y = r

        with self.fb_lock:
            self._fb_fill_rectangle(x0 + r, y0, x1 - r, y1, operation)

            while x <= y:
                if y > 0:
                    self._fb_draw_line(x1+x-r, y0-y+r, x1+x-r, y1+y-r, operation)
                    self._fb_draw_line(x0-x+r, y0-y+r, x0-x+r, y1+y-r, operation)
                if x > 0:
                    self._fb_draw_line(x0-y+r, y0-x+r, x0-y+r, y1+x-r, operation)
                    self._fb_draw_line(x1+y-r, y0-x+r, x1+y-r, y1+x-r, operation)
                if xd < 0:
                    xd += (x << 2) + 6
                else:
                    xd += ((x - y) << 2) + 10
                    y -= 1
                x += 1
            self._need_update = True

    def drawArc(self, x0, y0, r, s, operation):
        x0 = self._check_x(x0)
        y0 = self._check_y(x0)

        if r == 0 or s == 0:
            return
        
        with self.fb_lock:
            self._fb_draw_arc(x0, y0, r, s, operation)
            self._need_update = True

    def drawRoundRectangle(self, x0, y0, x1, y1, r, operation):
        x0 = self._check_x(x0)
        x1 = self._check_x(x1)
        y0 = self._check_y(y0)
        y1 = self._check_y(y1)

        if x1 < x0:
            x0, x1 = swap(x0, x1)

        if y1 < y0:
            y0, y1 = swap(y0, y1)

        if r < 0:
            r = 0

        with self.fb_lock:
            self._fb_draw_line(x0+r, y0, x1-r, y0, operation)
            self._fb_draw_line(x0+r, y1, x1-r, y1, operation)
            self._fb_draw_line(x0, y0+r, x0, y1-r, operation)
            self._fb_draw_line(x1, y0+r, x1, y1-r, operation)
            self._fb_draw_arc(x0+r, y0+r, r, 0x0C, operation)
            self._fb_draw_arc(x1-r, y0+r, r, 0x03, operation)
            self._fb_draw_arc(x0+r, y1-r, r, 0x30, operation)
            self._fb_draw_arc(x1-r, y1-r, r, 0xC0, operation)

            self._need_update = True

    def drawCircle(self, x0, y0, r, operation):
        x0 = self._check_x(x0)
        y0 = self._check_y(y0)

        if x0 < 0 or y0 < 0 or r <= 0:
            return
        
        while not self._check_radius(x0, y0, r):
            r -= 1
        
        xd = 1 - (r << 1)
        yd = 0
        e = 0
        x = r
        y = 0
        
        with self.fb_lock:
            while x >= y:
                self._fb_set_pixel(x0-x, y0+y, operation)
                self._fb_set_pixel(x0-x, y0-y, operation)
                self._fb_set_pixel(x0+x, y0+y, operation)
                self._fb_set_pixel(x0+x, y0-y, operation)
                self._fb_set_pixel(x0-y, y0+x, operation)
                self._fb_set_pixel(x0-y, y0-x, operation)
                self._fb_set_pixel(x0+y, y0+x, operation)
                self._fb_set_pixel(x0+y, y0-x, operation)

                y += 1
                e += yd
                yd += 2
                if (e << 1) +xd > 0:
                    x -= 1
                    e += xd
                    xd += 2

            self._need_update = True

    def fillCircle(self, x0, y0, r, operation):
        x0 = self._check_x(x0)
        y0 = self._check_y(y0)

        if x0 < 0 or y0 < 0 or r <= 0:
            return
        
        while not self._check_radius(x0, y0, r):
            r -= 1
        
        xd = 3 - (r << 1)
        x = 0
        y = r

        with self.fb_lock:
            while x <= y:
                if y > 0:
                    self._fb_draw_line(x0-x, y0-y, x0-x, y0+y, operation)
                    self._fb_draw_line(x0+x, y0-y, x0+x, y0+y, operation)
                if x > 0:
                    self._fb_draw_line(x0-y, y0-x, x0-y, y0+x, operation)
                    self._fb_draw_line(x0+y, y0-x, x0+y, y0+x, operation)
                if xd < 0:
                    xd += (x << 2) + 6
                else:
                    xd += ((x - y) << 2) + 10
                    y -= 1
                x += 1

        self._need_update = True
        self.drawCircle(x0, y0, r, operation)

    def fontSet(self, font_file):
        with open(font_file, "r") as font_fd:
            font = json.loads(font_fd.read())

        if not font:
            return False
        
        self._font_width = font.get("width")
        self._font_hight = font.get("hight")
        self._font = font.get("chars")

        if self._font_width and self._font_hight and self._font:
            return True
        return False

    def putChar(self, char, x0, y0, operation):
        x0 = self._check_x(x0)
        y0 = self._check_y(y0)

        if x0 < 0 or y0 < 0:
            return
        
        if not self._font_width or not self._font_hight or not self._font:
            return
        
        with self.fb_lock:
            self._fb_put_char(char, x0, y0, operation)

            self._need_update = True

    def putString(self, strng, x0, y0, operation):
        x0 = self._check_x(x0)
        y0 = self._check_y(y0)

        if x0 < 0 or y0 < 0:
            return
        
        if not self._font_width or not self._font_hight or not self._font:
            return
        
        with self.fb_lock:
            for char in strng:
                if x0 + self._font_width >= self.LCD_WIDTH:
                    break

                x0 = self._fb_put_char(char, x0, y0, operation)
                x0 += 1

            self._need_update = True
