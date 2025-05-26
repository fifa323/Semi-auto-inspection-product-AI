import serial

connect = ['80','02 30 32 41 30 32 44 03',
            '02 30 37 43 31 50 52 30 32 37 45 41 03',
            '02 30 32 41 30 32 44 03',
            '02 30 37 43 31 50 52 30 32 38 45 39 03',
            '02 30 32 41 30 32 44 03',
            '02 30 37 43 31 50 52 30 34 37 45 38 03',
            '02 30 32 41 30 32 44 03',
            '02 30 37 43 31 50 52 30 34 38 45 37 03',
            '02 30 32 41 30 32 44 03',
            '02 30 37 43 31 50 52 30 36 37 45 36 03',
            '02 30 32 41 30 32 44 03',
            '02 30 37 43 31 50 52 30 36 38 45 35 03',
            '02 30 32 41 30 32 44 03']

origin = ['02 30 34 43 35 4F 47 38 45 03',
            '02 30 32 41 34 32 39 03',
            '02 30 34 43 31 58 59 37 37 03',
            '02 30 32 41 30 32 44 03',
            '02 30 34 43 31 58 59 37 37 03',
            '02 30 32 41 30 32 44 03']

close = [' 02 30 34 43 35 45 44 39 42 03',
        '02 30 32 41 30 32 44 03']

operrateMode = ['02 30 34 43 31 50 4C 38 43 03','02 30 32 41 30 32 44 03',
                '02 30 32 41 30 32 44 03 ','02 30 34 43 31 53 54 38 31 03',
                '02 30 32 41 30 32 44 03']

exitMode = ['02 30 34 43 31 58 59 37 37 03','02 30 32 41 30 32 44 03']

clear = [  '02 30 34 43 31 50 4C 38 43 03',
            '02 30 32 41 30 32 44 03',
            '02 30 32 41 30 32 44 03',
            '02 30 34 43 31 53 54 38 31 03',
            '02 30 32 41 30 32 44 03', ]

start = [   '02 30 34 43 35 47 4F 38 45 03',
            '02 30 32 41 34 32 39 03',
            '02 30 34 43 31 58 59 37 37 03',
            '02 30 32 41 30 32 44 03']         # start program 1
move300 = ['02 31 39 43 35 4D 41 58 30 30 33 2E 30 30 59 30 30 30 2E 30 30 5A 30 30 30 2E 30 30 32 38 03']
move_end = [    '02 30 32 41 34 32 39 03',
                '02 30 34 43 31 58 59 37 37 03',
                '02 30 32 41 30 32 44 03']
m_start = '02 31 39 43 35 4D 41 58 '

class EZRobo():
    def __init__(self):
        self.s = serial.Serial(port= '/dev/ttyUSB0', baudrate = 9600, timeout=0.01)
        self.connect_robot()
        
    def connect_robot(self):
        #self.send_close()
        self.send(connect)
        #self.send(origin)
        
    def send_clear(self):
        print(">> send clear")
        self.send(clear)

    def send_close(self):
        self.send_clear()
        self.send(close)
        self.s.read(20)
        self.s.close()

    def send(self, data_list):
        #try:
        for data in data_list:
            byte_data = self.to_hex(data)
            #print(byte_data)
            self.s.write(byte_data)
            raw_output = ''
            while raw_output != '':
                raw_output = self.s.read(10).decode('utf-8', 'backslashreplace')
            print('raw: {}'.format(raw_output))
            while raw_output == '':
                raw_output = self.s.read(10).decode('utf-8', 'backslashreplace')
                    #print('raw: {}'.format(raw_output))
        #except:
            #pass

    def send_start(self, data_list):
        try:
            # print(data_list)
            self.s.write(self.to_hex(data_list[0]))
            # print(s.read())
            raw_output = ''
            while raw_output != '':
                raw_output = self.s.read(10).decode('utf-8', 'backslashreplace')
                # print('raw: {}'.format(raw_output))
            while raw_output == '':
                raw_output = self.s.read(10).decode('utf-8', 'backslashreplace')
                # print('raw: {}'.format(raw_output))
            while raw_output != '':
                raw_output = self.s.read(10).decode('utf-8', 'backslashreplace')
            for data in data_list[1:]:
                # print(data)
                self.s.write(self.to_hex(data))
                # print(s.read())
                raw_output = ''
                while raw_output == '':
                    raw_output = self.s.read(10).decode('utf-8', 'backslashreplace')
                    # print('raw: {}'.format(raw_output))
                while raw_output != '':
                    raw_output = self.s.read(10).decode('utf-8', 'backslashreplace')
                    # print('raw: {}'.format(raw_output))

        except:
            pass
            
    def to_hex(self, s):
        s = s.replace(' ','')
        hex_bytes = bytes.fromhex(s)
        return hex_bytes

    def val_translate(self, position):
        pos_ret = []
        for i in position:
            i_str = str(float(i))
            i_list = i_str.split('.')
            if int(i_list[0]) < 10:
                i_list[0] = '00' + i_list[0]
            elif int(i_list[0]) < 100:
                i_list[0] = '0' + i_list[0]
            
            #print(i_list[0])

            if len(i_list[1]) < 2:
                i_list[1] = i_list[1] + '0'
            #print(i_list[1])
            s_ret = ''
            s = ''.join([hex(ord(x)) for x in i_list[0]])
            s_strip = s.replace('0x', ' ')
            s_ret += s_strip
            s_ret += ' 2E'
            s = ''.join([hex(ord(x)) for x in i_list[1]])
            s_strip = s.replace('0x', ' ')
            s_ret += s_strip
            s_ret += ' '
            pos_ret.append(s_ret)
        return pos_ret[0], pos_ret[1], pos_ret[2]
            

    def chk_translate(self, position):
        sum_digit = 0
        for p in position:
            for s in str(p):
                if s != '0' and s != '.' and s != '-':
                    sum_digit += int(s)
        #print('sumdigit = ',sum_digit)

        s = 43-sum_digit
        #print(s)
        if s < 0 :
            s = s + 256
            #print("S - 265 = ",s)

        s = str(hex(s).upper())
        #print("B_strip = ",s)
        s_strip = s.lstrip('0X')
        #print('Lstrip = ',s_strip)
        if len(s_strip) == 0: 
            s_strip = '00'
        elif len(s_strip) < 2:
            s_strip = '0' + s_strip 

        #print('strip = ',s_strip)
        s = ''.join([hex(ord(x)) for x in s_strip])
        #print('s1 = ',s)
        s_strip = s.replace('0x', ' ')
        #print('strip1 = ',s_strip)
        return s_strip

    def get_position(self, position):
        x, y, z = self.val_translate(position)
        chksum = self.chk_translate(position)
        ret = m_start + x + ' 59 ' + y + ' 5A ' + z + chksum + ' 03 '
        return ret

    def move(self, position):
        param = [self.get_position(position)] + move_end
        # print(param)
        self.send_start(param)
        self.send_start(param)

    def Tmove(self, position):
        move_end = [    '02 30 32 41 34 32 39 03',
                    '02 30 34 43 31 58 59 37 37 03',
                    '02 30 32 41 30 32 44 03']
        param = [self.get_position(position)] + move_end
        # print(param)
        self.send_start(param)
        self.send_start(param)

    def toOrigin(self):
        self.send(origin)
        
if __name__ == "__main__":
    robot = EZRobo()
    robot.send_close()
