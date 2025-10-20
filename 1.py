# -*- coding: utf-8 -*- # يحدد ترميز الملف ليكون UTF-8، مما يسمح بكتابة الأحرف العربية في الكود والمخرجات.
# استيراد المكتبات اللازمة # قسم استيراد المكتبات التي يحتاجها البرنامج ليعمل.
import socket # لاستخدام المقابس (Sockets) في إنشاء الاتصالات الشبكية بين الخادم والعملاء.
import threading # للسماح بتشغيل عدة أجزاء من الكود بشكل متزامن (مثل إرسال واستقبال الفيديو والصوت في نفس الوقت).
import cv2 # مكتبة OpenCV لمعالجة الفيديو، تُستخدم هنا لالتقاط الصور من الكاميرا وضغطها.
import pyaudio # للتعامل مع الصوت، تُستخدم لتسجيل الصوت من الميكروفون وتشغيله على السماعات.
import pickle # لتحويل كائنات بايثون (مثل القوائم والقواميس) إلى سلسلة من البايتات لإرسالها عبر الشبكة والعكس.
import struct # للتعامل مع البيانات الثنائية (binary data)، لكنه غير مستخدم بشكل مباشر هنا ويمكن إزالته.
import sys # للتحكم في بيئة تشغيل بايثون، يُستخدم هنا لإغلاق البرنامج بشكل كامل.
import numpy as np # مكتبة للتعامل مع المصفوفات الرقمية، تُستخدم لتحويل بيانات الصورة.
from PIL import Image, ImageTk # مكتبة Pillow (PIL) لمعالجة الصور وتحويلها إلى صيغة متوافقة مع واجهة Tkinter.
import tkinter as tk # المكتبة الأساسية لإنشاء الواجهات الرسومية (GUI).
from tkinter import messagebox, simpledialog # وحدات فرعية من Tkinter لعرض مربعات الحوار (مثل رسائل الخطأ أو طلب الإدخال).
import ttkbootstrap as ttk # مكتبة لتجميل واجهات Tkinter وإعطائها مظهراً عصرياً.
from ttkbootstrap.constants import * # لاستيراد الثوابت المعرفة مسبقاً في ttkbootstrap (مثل أسماء الألوان والأنماط).
import time # للتحكم في التوقيت، مثل إيقاف التنفيذ مؤقتاً.
import queue # لتنظيم البيانات في طوابير، يُستخدم هنا لتمرير الإشعارات بأمان بين الخيوط والواجهة الرسومية.

# --- إعدادات أساسية ---
IMAGE_QUALITY = 40  # متغير لتحديد جودة الصورة المضغوطة (بصيغة JPEG) عند إرسالها. قيمة أقل تعني ضغطاً أعلى وحجماً أصغر.

# دالة للحصول على عنوان IP المحلي
def get_local_ip(): # تعريف دالة للحصول على عنوان IP الخاص بالجهاز على الشبكة المحلية.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # إنشاء مقبس من نوع UDP (لإرسال البيانات بدون اتصال مسبق).
    try: # بدء كتلة try لاحتواء الكود الذي قد يسبب خطأ.
        # لا يجب أن يكون العنوان قابلاً للوصول
        s.connect(('10.255.255.255', 1)) # محاولة الاتصال بعنوان IP وهمي غير قابل للوصول.
        IP = s.getsockname()[0] # نظام التشغيل سيقوم بتعيين عنوان IP المحلي للمقبس لمحاولة هذا الاتصال، ونحن نستخرجه هنا.
    except Exception: # في حال فشل محاولة الاتصال (لأي سبب).
        IP = '127.0.0.1' # يتم تعيين عنوان IP الافتراضي (localhost) كحل بديل.
    finally: # هذا الجزء من الكود يتم تنفيذه دائماً، سواء نجح الـ try أو فشل.
        s.close() # إغلاق المقبس لتحرير الموارد التي كان يستخدمها.
    return IP # إرجاع عنوان IP الذي تم الحصول عليه.

# --- فئة الخادم (Server) - أصبحت الآن مركز التحكم ---
class Server: # تعريف فئة (Class) الخادم التي ستدير جلسة الدردشة بأكملها.
    def __init__(self, host, video_port, audio_port, control_port): # الدالة المُنشِئة (constructor) التي يتم استدعاؤها عند إنشاء كائن جديد من هذه الفئة.
        self.host = host # تخزين عنوان IP الخاص بالخادم.
        self.ports = {'video': video_port, 'audio': audio_port, 'control': control_port} # قاموس لتخزين أرقام المنافذ للفيديو والصوت والتحكم.
        self.clients = {}  # قاموس لتخزين معلومات العملاء المتصلين. المفتاح هو عنوان العميل (IP, port) والقيمة هي معلوماته (مثل الاسم).
        self.admin_addr = (host, control_port) # عنوان المشرف (admin) هو نفس عنوان الخادم.
        self.running = False # متغير منطقي (boolean) لتتبع ما إذا كان الخادم يعمل أم لا.
        self.lock = threading.Lock() # إنشاء قفل (lock) لمنع حدوث تضارب عند وصول خيوط متعددة إلى البيانات المشتركة (مثل قاموس العملاء) في نفس الوقت.
        self.message_queue = queue.Queue()  # إنشاء طابور لتخزين الرسائل، ولكنه غير مستخدم حاليًا في هذه الفئة.

    def start(self): # دالة لبدء تشغيل الخادم.
        self.running = True # تغيير حالة الخادم إلى "يعمل".
        self.sockets = {} # قاموس لتخزين كائنات المقابس (sockets) الخاصة بالخادم.
        for medium in self.ports: # حلقة تكرارية تمر على أنواع الاتصالات (فيديو، صوت، تحكم).
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # إنشاء مقبس UDP لكل نوع اتصال.
            s.bind((self.host, self.ports[medium])) # ربط المقبس بعنوان IP ومنفذ الخادم، ليكون جاهزاً لاستقبال البيانات على هذا العنوان.
            self.sockets[medium] = s # إضافة المقبس الذي تم إنشاؤه إلى قاموس المقابس.
            
            thread = threading.Thread(target=self.handle_stream, args=(medium,)) # إنشاء خيط (thread) جديد لكل مقبس. مهمة الخيط هي تشغيل دالة handle_stream.
            thread.daemon = True # جعل الخيط "خيطاً خادماً"، مما يعني أنه سيتم إغلاقه تلقائياً عند إغلاق البرنامج الرئيسي.
            thread.start() # بدء تشغيل الخيط.
        
        print(f"✅ الخادم يعمل على العنوان: {self.host} بالمنافذ: {self.ports}") # طباعة رسالة تأكيد بأن الخادم قد بدأ بنجاح.

    def stop(self): # دالة لإيقاف الخادم.
        self.running = False # تغيير حالة الخادم إلى "متوقف" لإيقاف الحلقات التكرارية في الخيوط.
        # إرسال أمر إغلاق لجميع العملاء
        for addr in list(self.clients.keys()): # حلقة تكرارية على جميع العملاء المسجلين.
            self.send_control_message({'command': 'server_shutdown'}, addr) # إرسال رسالة تحكم لكل عميل لإعلامه بأن الخادم يتم إغلاقه.

        for s in self.sockets.values(): # حلقة تكرارية على جميع مقابس الخادم.
            s.close() # إغلاق كل مقبس لتحرير المنفذ والموارد.
        print("🛑 تم إيقاف الخادم.") # طباعة رسالة تأكيد بأن الخادم قد توقف.

    def handle_stream(self, medium): # الدالة التي تعمل داخل كل خيط من خيوط الخادم، مسؤولة عن استقبال البيانات.
        sock = self.sockets[medium] # الحصول على المقبس المناسب من القاموس بناءً على نوع البيانات (فيديو، صوت، تحكم).
        while self.running: # حلقة تكرارية تستمر طالما أن الخادم في حالة "يعمل".
            try: # بدء كتلة try لاحتواء الكود الذي قد يسبب خطأ.
                data, addr = sock.recvfrom(65536) # انتظار واستقبال البيانات من أي عميل. `recvfrom` تعيد البيانات وعنوان المرسل.
                if not self.running: break # إذا تم إيقاف الخادم أثناء انتظار البيانات، اخرج من الحلقة.
                
                if medium == 'control': # إذا كانت البيانات قادمة عبر منفذ التحكم.
                    self.process_control_message(data, addr) # استدعاء دالة معالجة رسائل التحكم.
                else: # إذا كانت البيانات فيديو أو صوت.
                    # إضافة العميل إذا لم يكن موجوداً (للاتصالات الأولى)
                    if addr not in self.clients: # التحقق مما إذا كان هذا العميل جديداً.
                        self.add_client(addr, "مشارك جديد") # إضافة العميل الجديد إلى القائمة باسم افتراضي.
                    # بث البيانات للآخرين
                    self.broadcast(data, addr, medium) # إعادة إرسال (بث) البيانات المستلمة إلى جميع العملاء الآخرين.
            except Exception as e: # في حال حدوث أي خطأ أثناء استقبال البيانات.
                if self.running: print(f"خطأ في الخادم ({medium}): {e}") # طباعة رسالة الخطأ إذا كان الخادم لا يزال يعمل.
                break # الخروج من الحلقة في حالة حدوث خطأ.

    def process_control_message(self, data, addr): # دالة لمعالجة رسائل الأوامر والتحكم.
        try: # بدء كتلة try لاحتواء الكود الذي قد يسبب خطأ.
            message = pickle.loads(data) # فك "تغليف" البيانات المستلمة (التي تم إرسالها باستخدام pickle) لتحويلها مرة أخرى إلى كائن بايثون.
            command = message.get('command') # الحصول على نوع الأمر من الرسالة.

            if command == 'join': # إذا كان الأمر هو "انضمام".
                self.add_client(addr, message.get('name', 'مجهول')) # إضافة العميل الجديد إلى قائمة العملاء.
            
            elif command == 'leave': # إذا كان الأمر هو "مغادرة".
                self.remove_client(addr) # إزالة العميل من قائمة العملاء.
                
            elif command == 'mute_status': # إذا كان الأمر هو "حالة الكتم".
                # إرسال إشعار كتم الصوت للجميع
                client_name = self.clients.get(addr, {}).get('name', 'مجهول') # الحصول على اسم العميل الذي أرسل الحالة.
                mute_status = message.get('status', False) # الحصول على حالة الكتم (صامت أم لا).
                status_text = "كتم" if mute_status else "إلغاء كتم" # تحديد نص الإشعار بناءً على الحالة.
                notification = f"تم {status_text} صوت {client_name}" # إنشاء رسالة الإشعار الكاملة.
                
                # إرسال الإشعار لجميع العملاء بما فيهم المشرف
                for client_addr in list(self.clients.keys()): # حلقة تكرارية على جميع العملاء.
                    self.send_control_message({ # إنشاء رسالة إشعار.
                        'command': 'notification', 
                        'message': notification
                    }, client_addr) # إرسال رسالة الإشعار إلى العميل.

            # أوامر المشرف
            elif addr[0] == self.host: # التحقق من أن الرسالة قادمة من المشرف (عن طريق مقارنة IP المرسل بـ IP الخادم).
                target_addr = tuple(message.get('target_addr')) # الحصول على عنوان العميل المستهدف بالإجراء.
                if command == 'admin_mute': # إذا كان الأمر هو "كتم من قبل المشرف".
                    self.send_control_message({'command': 'force_mute', 'status': True}, target_addr) # إرسال أمر "كتم إجباري" للعميل المستهدف.
                elif command == 'admin_unmute': # إذا كان الأمر هو "إلغاء كتم من قبل المشرف".
                    self.send_control_message({'command': 'force_mute', 'status': False}, target_addr) # إرسال أمر "إلغاء كتم إجباري".
                elif command == 'admin_stop_video': # إذا كان الأمر هو "إيقاف كاميرا من قبل المشرف".
                    self.send_control_message({'command': 'force_video_off', 'status': True}, target_addr) # إرسال أمر "إيقاف كاميرا إجباري".
                elif command == 'admin_start_video': # إذا كان الأمر هو "تشغيل كاميرا من قبل المشرف".
                    self.send_control_message({'command': 'force_video_off', 'status': False}, target_addr) # إرسال أمر "تشغيل كاميرا إجباري".
                elif command == 'admin_kick': # إذا كان الأمر هو "طرد من قبل المشرف".
                    self.send_control_message({'command': 'kick'}, target_addr) # إرسال أمر "طرد" للعميل المستهدف.
                    self.remove_client(target_addr) # إزالة العميل المطرود من قائمة الخادم.

        except Exception as e: # في حال حدوث أي خطأ أثناء معالجة الرسالة.
            print(f"خطأ في معالجة رسالة التحكم: {e}") # طباعة رسالة الخطأ.

    def add_client(self, addr, name): # دالة لإضافة عميل جديد.
        with self.lock: # استخدام القفل لضمان عدم حدوث تضارب في البيانات.
            if addr not in self.clients: # التحقق من أن العميل غير موجود بالفعل.
                self.clients[addr] = {'name': name} # إضافة العميل إلى قاموس العملاء.
                print(f"➕ انضم: {name} ({addr})") # طباعة رسالة في طرفية الخادم.
                
                # إرسال إشعار الانضمام للجميع
                notification = f"انضم {name} إلى الدردشة" # إنشاء رسالة إشعار.
                for client_addr in list(self.clients.keys()): # حلقة تكرارية على جميع العملاء.
                    self.send_control_message({ # إنشاء رسالة الإشعار.
                        'command': 'notification', 
                        'message': notification
                    }, client_addr) # إرسال الإشعار للعميل.
                
                self.broadcast_client_list() # استدعاء دالة لتحديث قائمة العملاء لدى المشرف.

    def remove_client(self, addr): # دالة لإزالة عميل.
        with self.lock: # استخدام القفل لضمان عدم حدوث تضارب في البيانات.
            if addr in self.clients: # التحقق من وجود العميل في القائمة.
                name = self.clients[addr]['name'] # الحصول على اسم العميل قبل حذفه.
                del self.clients[addr] # حذف العميل من قاموس العملاء.
                print(f"➖ غادر: {name} ({addr})") # طباعة رسالة في طرفية الخادم.
                
                # إرسال إشعار المغادرة للجميع
                notification = f"غادر {name} الدردشة" # إنشاء رسالة إشعار بالمغادرة.
                for client_addr in list(self.clients.keys()): # حلقة تكرارية على العملاء المتبقين.
                    self.send_control_message({ # إنشاء رسالة الإشعار.
                        'command': 'notification', 
                        'message': notification
                    }, client_addr) # إرسال الإشعار للعميل.
                
                self.broadcast_client_list() # استدعاء دالة لتحديث قائمة العملاء لدى المشرف.

    def broadcast_client_list(self): # دالة لإرسال قائمة العملاء المحدثة.
        # يرسل قائمة العملاء المحدثة للمشرف فقط
        client_list_for_admin = {str(k): v for k, v in self.clients.items()} # تحويل قاموس العملاء إلى صيغة مناسبة للإرسال (تحويل المفتاح tuple إلى نص).
        admin_addr = (self.host, self.ports['control']) # تحديد عنوان المشرف.
        self.send_control_message({'command': 'update_list', 'clients': client_list_for_admin}, admin_addr) # إرسال القائمة المحدثة إلى المشرف.

    def send_control_message(self, message, addr): # دالة مساعدة لإرسال رسائل التحكم.
        try: # بدء كتلة try لاحتواء الكود الذي قد يسبب خطأ.
            self.sockets['control'].sendto(pickle.dumps(message), addr) # "تغليف" الرسالة باستخدام pickle وإرسالها إلى العنوان المحدد عبر مقبس التحكم.
        except Exception as e: # في حال فشل الإرسال.
            print(f"فشل إرسال رسالة التحكم إلى {addr}: {e}") # طباعة رسالة خطأ.

    def broadcast(self, data, sender_addr, medium): # دالة لبث (إعادة إرسال) بيانات الفيديو أو الصوت للجميع.
        sock = self.sockets[medium] # الحصول على المقبس المناسب (فيديو أو صوت).
        for addr in list(self.clients.keys()): # حلقة تكرارية على جميع العملاء.
            # لا ترسل البيانات إلى المرسل نفسه
            if addr != sender_addr: # التحقق من أن عنوان العميل الحالي في الحلقة ليس هو نفسه عنوان مرسل البيانات الأصلي.
                try: # بدء كتلة try لاحتواء الكود الذي قد يسبب خطأ.
                    sock.sendto(data, addr) # إرسال البيانات إلى العميل.
                except Exception as e: # في حال فشل الإرسال.
                    print(f"فشل في بث البيانات إلى {addr}: {e}") # طباعة رسالة خطأ.


# --- فئة التطبيق الرئيسية (GUI) ---
class ChatApp(ttk.Window): # تعريف فئة التطبيق الرئيسية التي ترث من ttk.Window لإنشاء النافذة الأساسية.
    def __init__(self): # الدالة المُنشِئة (constructor) للواجهة الرسومية.
        super().__init__(themename="superhero", title="تطبيق الاتصال الجماعي2") # استدعاء مُنشِئ الفئة الأم مع تحديد السمة (theme) وعنوان النافذة.
        self.geometry("500x350") # تحديد الأبعاد الأولية للنافذة.
        self.protocol("WM_DELETE_WINDOW", self.on_closing) # ربط حدث إغلاق النافذة (الضغط على زر X) بدالة on_closing لتنفيذ الإجراءات اللازمة قبل الخروج.

        self.server = None # متغير لتخزين كائن الخادم (فقط إذا كان المستخدم هو المشرف).
        self.is_running = False # متغير لتتبع ما إذا كان العميل متصلاً حالياً أم لا.
        self.is_admin = False # متغير لتحديد ما إذا كان المستخدم الحالي هو المشرف.
        
        self.video_port = 9999 # تحديد رقم المنفذ الافتراضي للفيديو.
        self.audio_port = 8888 # تحديد رقم المنفذ الافتراضي للصوت.
        self.control_port = 7777 # تحديد رقم المنفذ الافتراضي للتحكم.
        
        self.notification_queue = queue.Queue() # إنشاء طابور لتلقي الإشعارات من خيوط الشبكة وعرضها بأمان في الواجهة الرسومية.
        self.after(100, self.process_notifications) # جدولة تشغيل دالة process_notifications بعد 100 ميلي ثانية للبدء في معالجة الإشعارات.

        self.create_welcome_widgets() # استدعاء دالة لإنشاء واجهة البداية (شاشة الترحيب).

    def process_notifications(self): # دالة لمعالجة الإشعارات الموجودة في الطابور.
        try: # بدء كتلة try.
            while True: # حلقة لمحاولة تفريغ الطابور من كل الرسائل الموجودة فيه.
                message = self.notification_queue.get_nowait() # محاولة الحصول على رسالة من الطابور بدون انتظار (إذا كان فارغاً، سيحدث خطأ).
                self.show_notification(message) # إذا تم الحصول على رسالة، يتم عرضها كإشعار.
        except queue.Empty: # هذا الخطأ يحدث عندما يكون الطابور فارغاً، وهو أمر طبيعي.
            pass # لا تفعل شيئاً، فقط استمر.
        finally: # هذا الجزء يتم تنفيذه دائماً.
            self.after(100, self.process_notifications) # جدولة تشغيل هذه الدالة مرة أخرى بعد 100 ميلي ثانية للتحقق من وجود إشعارات جديدة.

    def show_notification(self, message): # دالة لعرض نافذة منبثقة كإشعار.
        # إنشاء نافذة منبثقة للإشعار
        top = ttk.Toplevel(self) # إنشاء نافذة جديدة فوق النافذة الرئيسية.
        top.title("إشعار") # تحديد عنوان النافذة المنبثقة.
        top.geometry("300x100") # تحديد أبعاد النافذة المنبثقة.
        top.transient(self) # ربط النافذة المنبثقة بالنافذة الرئيسية (تبقى فوقها دائماً).
        top.grab_set() # جعل النافذة المنبثقة "مشروطة" (modal)، أي لا يمكن التفاعل مع النافذة الرئيسية حتى يتم إغلاقها.
        
        ttk.Label(top, text=message, padding=10).pack(expand=True) # إضافة ملصق (label) لعرض نص الإشعار داخل النافذة.
        ttk.Button(top, text="موافق", command=top.destroy, bootstyle=SUCCESS).pack(pady=5) # إضافة زر "موافق" لإغلاق النافذة.
        
        # إغلاق النافذة تلقائياً بعد 3 ثوان
        top.after(3000, top.destroy) # جدولة إغلاق النافذة تلقائياً بعد 3000 ميلي ثانية (3 ثوان).

    def create_welcome_widgets(self): # دالة لإنشاء عناصر واجهة شاشة البداية.
        self.welcome_frame = ttk.Frame(self, padding=20) # إنشاء إطار (frame) لاحتواء عناصر الواجهة.
        self.welcome_frame.pack(expand=True, fill=BOTH) # وضع الإطار في النافذة وتوسيعه لملء المساحة المتاحة.

        ttk.Label(self.welcome_frame, text="مرحباً بك في تطبيق الاتصال", font=("Helvetica", 16, "bold")).pack(pady=10) # إضافة عنوان ترحيبي.
        
        ttk.Button(self.welcome_frame, text="👑 إنشاء جلسة (مشرف)", command=self.start_server, bootstyle=SUCCESS).pack(pady=10, fill=X, ipady=5) # إضافة زر "إنشاء جلسة" وربطه بدالة start_server.
        
        ttk.Separator(self.welcome_frame, orient=HORIZONTAL).pack(pady=10, fill=X) # إضافة خط فاصل أفقي.

        f = ttk.Frame(self.welcome_frame) # إنشاء إطار فرعي لتنظيم حقل الإدخال والملصق الخاص به.
        f.pack(pady=5, fill=X, expand=True) # وضع الإطار الفرعي في النافذة.
        ttk.Label(f, text="أدخل IP الخادم:").pack(side=RIGHT, padx=5) # إضافة ملصق "أدخل IP الخادم".
        self.ip_entry = ttk.Entry(f, bootstyle=INFO) # إنشاء حقل لإدخال النص (IP).
        self.ip_entry.pack(side=LEFT, fill=X, expand=True) # وضع حقل الإدخال في النافذة.
        self.ip_entry.insert(0, "127.0.0.1")  # وضع قيمة افتراضية (localhost) في حقل الإدخال.
        
        ttk.Button(self.welcome_frame, text="🔗 الانضمام لجلسة", command=self.show_join_options, bootstyle=PRIMARY).pack(pady=10, fill=X, ipady=5) # إضافة زر "الانضمام لجلسة" وربطه بدالة show_join_options.

    def start_server(self): # دالة يتم استدعاؤها عند الضغط على زر "إنشاء جلسة".
        try: # بدء كتلة try لاحتواء الكود الذي قد يسبب خطأ.
            self.is_admin = True # تعيين المستخدم الحالي كمشرف.
            host_ip = get_local_ip() # الحصول على عنوان IP المحلي للجهاز.
            self.server = Server(host_ip, self.video_port, self.audio_port, self.control_port) # إنشاء كائن جديد من فئة الخادم.
            self.server.start() # بدء تشغيل الخادم.
            
            # بدء العميل بعد تأكيد أن الخادم يعمل
            self.after(100, lambda: self.start_client(host_ip, "المشرف 👑", True, True)) # جدولة بدء العميل الخاص بالمشرف بعد فترة قصيرة للتأكد من أن الخادم جاهز.
            
        except Exception as e: # في حال حدوث خطأ أثناء بدء الخادم.
            messagebox.showerror("خطأ", f"فشل في بدء الخادم: {e}") # عرض رسالة خطأ للمستخدم.
            print(f"خطأ في بدء الخادم: {e}") # طباعة الخطأ في الطرفية للمطور.

    def show_join_options(self): # دالة يتم استدعاؤها عند الضغط على زر "الانضمام لجلسة".
        server_ip = self.ip_entry.get() # الحصول على عنوان IP الذي أدخله المستخدم.
        if not server_ip: # التحقق من أن المستخدم أدخل عنوان IP.
            messagebox.showerror("خطأ", "الرجاء إدخال عنوان IP الخاص بالخادم") # عرض رسالة خطأ إذا كان الحقل فارغاً.
            return # الخروج من الدالة.

        name = simpledialog.askstring("اسمك", "الرجاء إدخال اسمك:", parent=self) # عرض مربع حوار لطلب اسم المستخدم.
        if not name: return # إذا أغلق المستخدم المربع أو لم يدخل اسماً، اخرج من الدالة.

        # نافذة منبثقة لاختيارات الانضمام
        top = ttk.Toplevel(self) # إنشاء نافذة منبثقة جديدة.
        top.title("خيارات الانضمام") # تحديد عنوان النافذة.
        top.geometry("300x250") # تحديد أبعاد النافذة.
        ttk.Label(top, text="كيف تريد الانضمام؟", font=("Helvetica", 14)).pack(pady=10) # إضافة ملصق توضيحي.
        
        video_var = tk.BooleanVar(value=True) # إنشاء متغير منطقي لتخزين حالة خيار الكاميرا (افتراضياً مفعل).
        audio_var = tk.BooleanVar(value=True) # إنشاء متغير منطقي لتخزين حالة خيار الصوت (افتراضياً مفعل).
        
        ttk.Checkbutton(top, text="المشاركة بالكاميرا", variable=video_var, bootstyle="round-toggle").pack(pady=5) # إضافة مربع اختيار للكاميرا.
        ttk.Checkbutton(top, text="المشاركة بالصوت", variable=audio_var, bootstyle="round-toggle").pack(pady=5) # إضافة مربع اختيار للصوت.

        def on_join(): # تعريف دالة داخلية ليتم استدعاؤها عند الضغط على زر الانضمام في النافذة المنبثقة.
            top.destroy() # إغلاق النافذة المنبثقة.
            self.start_client(server_ip, name, video_var.get(), audio_var.get()) # بدء العميل مع الخيارات التي حددها المستخدم.

        ttk.Button(top, text="انضمام", command=on_join, bootstyle=SUCCESS).pack(pady=20) # إضافة زر "انضمام" وربطه بدالة on_join.
        
    def start_client(self, server_ip, name, join_with_video, join_with_audio): # دالة لبدء تشغيل العميل (سواء كان مشرفاً أو مشاركاً).
        try: # بدء كتلة try لاحتواء الكود الذي قد يسبب خطأ.
            self.is_running = True # تعيين حالة العميل إلى "يعمل".
            if hasattr(self, 'welcome_frame'): # التحقق من وجود إطار شاشة الترحيب.
                self.welcome_frame.destroy() # إزالة إطار شاشة الترحيب للانتقال إلى واجهة الدردشة.
            self.create_chat_widgets() # إنشاء عناصر واجهة الدردشة.
            self.setup_client_threads(server_ip, name, join_with_video, join_with_audio) # إعداد وبدء خيوط الشبكة والصوت والفيديو.
        except Exception as e: # في حال حدوث خطأ.
            messagebox.showerror("خطأ", f"فشل في بدء العميل: {e}") # عرض رسالة خطأ.
            print(f"خطأ في بدء العميل: {e}") # طباعة الخطأ في الطرفية.

    def setup_client_threads(self, server_ip, name, send_video, send_audio): # دالة لإعداد خيوط العميل.
        self.server_ip = server_ip # تخزين عنوان IP الخاص بالخادم.
        self.name = name # تخزين اسم المستخدم.
        self.send_video_flag = send_video # تخزين خيار إرسال الفيديو.
        self.send_audio_flag = send_audio # تخزين خيار إرسال الصوت.
        
        # إعداد الكاميرا والصوت
        self.p_audio = pyaudio.PyAudio() # تهيئة كائن PyAudio للتعامل مع الصوت.
        self.chunk_size = 1024 # تحديد حجم قطعة البيانات الصوتية التي سيتم قراءتها في كل مرة.
        
        # إنشاء منافذ للعميل (مختلفة عن منافذ الخادم)
        client_ports = { # تحديد أرقام منافذ مختلفة للعميل لتجنب التعارض مع الخادم إذا كانا على نفس الجهاز.
            'video': self.video_port + 1,
            'audio': self.audio_port + 1,
            'control': self.control_port + 1
        }
        
        self.sockets = {} # قاموس لتخزين مقابس العميل.
        for medium in client_ports: # حلقة تكرارية لإنشاء المقابس.
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # إنشاء مقبس UDP.
            # ربط المنافذ الخاصة بالعميل (للاستقبال فقط)
            try: # محاولة الربط بالمنفذ المحدد.
                s.bind(('0.0.0.0', client_ports[medium])) # الربط بـ '0.0.0.0' يعني أن المقبس يمكنه استقبال البيانات من أي واجهة شبكة على الجهاز.
            except: # إذا كان المنفذ محجوزاً.
                # إذا فشل الربط، نستخدم منفذ عشوائي
                s.bind(('0.0.0.0', 0)) # الربط بالمنفذ 0 يطلب من نظام التشغيل اختيار أي منفذ متاح.
            self.sockets[medium] = s # تخزين المقبس في القاموس.
        
        self.is_muted = not send_audio # تحديد الحالة الأولية للكتم (إذا لم يختر المستخدم إرسال الصوت، فإنه يعتبر صامتاً).
        self.is_video_off = not send_video # تحديد الحالة الأولية للكاميرا (إذا لم يختر المستخدم إرسال الفيديو، فإن الكاميرا تعتبر متوقفة).
        self.remote_video_labels = {} # قاموس لتخزين ملصقات الفيديو الخاصة بالمشاركين الآخرين.
        
        # إرسال طلب انضمام للخادم
        join_message = {'command': 'join', 'name': self.name} # إنشاء رسالة الانضمام.
        self.control_socket = self.sockets['control'] # الحصول على مقبس التحكم.
        self.control_socket.sendto(pickle.dumps(join_message), (server_ip, self.control_port)) # إرسال رسالة الانضمام إلى الخادم.

        # بدء الخيوط
        threads = [] # قائمة لتخزين الخيوط التي سيتم إنشاؤها.
        # خيوط الاستقبال تعمل دائماً
        threads.append(threading.Thread(target=self.receive_video)) # إنشاء خيط لاستقبال الفيديو.
        threads.append(threading.Thread(target=self.receive_audio)) # إنشاء خيط لاستقبال الصوت.
        threads.append(threading.Thread(target=self.receive_control)) # إنشاء خيط لاستقبال رسائل التحكم.
        
        if self.send_video_flag: # إذا اختار المستخدم المشاركة بالكاميرا.
            self.cap = cv2.VideoCapture(0) # تهيئة الكاميرا (0 تعني الكاميرا الافتراضية).
            if not self.cap.isOpened(): # التحقق من نجاح الاتصال بالكاميرا.
                messagebox.showwarning("تحذير", "تعذر الوصول إلى الكاميرا") # عرض تحذير في حال الفشل.
                self.send_video_flag = False # تعطيل إرسال الفيديو.
            else: # إذا نجح الاتصال بالكاميرا.
                threads.append(threading.Thread(target=self.send_video, args=(server_ip,))) # إنشاء خيط لإرسال الفيديو.
        
        if self.send_audio_flag: # إذا اختار المستخدم المشاركة بالصوت.
            try: # محاولة الوصول للميكروفون.
                self.audio_stream_in = self.p_audio.open(format=pyaudio.paInt16, channels=1, rate=20000, input=True, frames_per_buffer=self.chunk_size) # فتح مجرى صوتي للإدخال (الميكروفون).
                threads.append(threading.Thread(target=self.send_audio, args=(server_ip,))) # إنشاء خيط لإرسال الصوت.
                self.mute_button.config(text="🎤 كتم الصوت") # تحديث نص زر كتم الصوت.
            except Exception as e: # في حال فشل الوصول للميكروفون.
                messagebox.showwarning("تحذير", f"تعذر الوصول إلى الميكروفون: {e}") # عرض رسالة تحذير.
                self.send_audio_flag = False # تعطيل إرسال الصوت.
                self.mute_button.config(text="🔇 أنت صامت", state=DISABLED) # تعطيل زر كتم الصوت.
        else: # إذا لم يختر المستخدم المشاركة بالصوت من البداية.
             self.mute_button.config(text="🔇 أنت صامت", state=DISABLED) # تعطيل زر كتم الصوت.
        
        if not self.send_video_flag: # إذا لم يتم تفعيل إرسال الفيديو (سواء باختيار المستخدم أو بسبب خطأ).
            self.video_button.config(text="📷 الكاميرا مغلقة", state=DISABLED) # تعطيل زر الكاميرا.

        try: # محاولة الوصول لمخرج الصوت (السماعات).
            self.audio_stream_out = self.p_audio.open(format=pyaudio.paInt16, channels=1, rate=20000, output=True, frames_per_buffer=self.chunk_size) # فتح مجرى صوتي للإخراج (السماعات).
        except Exception as e: # في حال فشل الوصول للسماعات.
            messagebox.showwarning("تحذير", f"تعذر الوصول إلى مخرج الصوت: {e}") # عرض رسالة تحذير.

        for t in threads: # حلقة تكرارية على جميع الخيوط التي تم إنشاؤها.
            t.daemon = True # جعلها خيوطاً خادمة.
            t.start() # بدء تشغيل الخيوط.

    def create_chat_widgets(self): # دالة لإنشاء عناصر واجهة نافذة الدردشة.
        self.title("نافذة الاتصال") # تغيير عنوان النافذة.
        self.geometry("1000x750") # تغيير أبعاد النافذة.
        
        main_frame = ttk.Frame(self) # إنشاء إطار رئيسي لاحتواء كل العناصر.
        main_frame.pack(fill=BOTH, expand=True) # وضع الإطار في النافذة.
        
        # لوحة تحكم المشرف (تظهر فقط للمشرف)
        if self.is_admin: # التحقق مما إذا كان المستخدم هو المشرف.
            admin_panel = ttk.Labelframe(main_frame, text="لوحة تحكم المشرف", padding=10) # إنشاء إطار مع تسمية خاصة بلوحة تحكم المشرف.
            admin_panel.pack(side=RIGHT, fill=Y, padx=10, pady=10) # وضع اللوحة على يمين النافذة.
            
            # عرض IP المشرف
            ip_frame = ttk.Frame(admin_panel) # إنشاء إطار فرعي لعرض IP.
            ip_frame.pack(fill=X, pady=5) # وضع الإطار الفرعي في اللوحة.
            ttk.Label(ip_frame, text="IP المشرف:", font=("Helvetica", 10, "bold")).pack(side=RIGHT) # إضافة ملصق.
            ttk.Label(ip_frame, text=get_local_ip(), font=("Helvetica", 10)).pack(side=RIGHT, padx=5) # إضافة ملصق يعرض IP الخادم.
            
            ttk.Label(admin_panel, text="قائمة المشاركين:", font=("Helvetica", 10, "bold")).pack(anchor=W, pady=(10, 5)) # إضافة ملصق "قائمة المشاركين".
            
            # إطار لعرض قائمة المشاركين
            list_frame = ttk.Frame(admin_panel) # إنشاء إطار لاحتواء القائمة وشريط التمرير.
            list_frame.pack(fill=BOTH, expand=True, pady=5) # وضع الإطار في اللوحة.
            
            # شريط تمرير للقائمة
            scrollbar = ttk.Scrollbar(list_frame) # إنشاء شريط تمرير.
            scrollbar.pack(side=RIGHT, fill=Y) # وضع شريط التمرير على يمين الإطار.
            
            self.clients_tree = ttk.Treeview(list_frame, columns=('name', 'addr'), show='headings', # إنشاء عنصر Treeview لعرض قائمة المشاركين بشكل جدولي.
                                              bootstyle=INFO, yscrollcommand=scrollbar.set) # ربط شريط التمرير بـ Treeview.
            self.clients_tree.heading('name', text='الاسم') # تحديد عنوان العمود الأول.
            self.clients_tree.heading('addr', text='العنوان') # تحديد عنوان العمود الثاني.
            self.clients_tree.column('name', width=120) # تحديد عرض العمود الأول.
            self.clients_tree.column('addr', width=150) # تحديد عرض العمود الثاني.
            self.clients_tree.pack(fill=BOTH, expand=True) # وضع الـ Treeview في الإطار.
            
            scrollbar.config(command=self.clients_tree.yview) # ربط حركة شريط التمرير بالـ Treeview.

            btn_frame = ttk.Frame(admin_panel) # إنشاء إطار لاحتواء أزرار التحكم الخاصة بالمشرف.
            btn_frame.pack(fill=X, pady=5) # وضع الإطار في اللوحة.
            ttk.Button(btn_frame, text="كتم", command=lambda: self.admin_action('admin_mute'), bootstyle=SECONDARY).pack(side=LEFT, expand=True, padx=2) # إضافة زر "كتم" وربطه بدالة admin_action.
            ttk.Button(btn_frame, text="إلغاء الكتم", command=lambda: self.admin_action('admin_unmute'), bootstyle=SUCCESS).pack(side=LEFT, expand=True, padx=2) # إضافة زر "إلغاء الكتم".
            ttk.Button(btn_frame, text="إيقاف كاميرا", command=lambda: self.admin_action('admin_stop_video'), bootstyle=SECONDARY).pack(side=LEFT, expand=True, padx=2) # إضافة زر "إيقاف كاميرا".
            ttk.Button(btn_frame, text="تشغيل كاميرا", command=lambda: self.admin_action('admin_start_video'), bootstyle=SUCCESS).pack(side=LEFT, expand=True, padx=2) # إضافة زر "تشغيل كاميرا".
            ttk.Button(btn_frame, text="طرد", command=lambda: self.admin_action('admin_kick'), bootstyle=DANGER).pack(side=LEFT, expand=True, padx=2) # إضافة زر "طرد".


        # إطار الفيديوهات
        self.videos_frame = ttk.Frame(main_frame) # إنشاء إطار لعرض نوافذ الفيديو.
        self.videos_frame.pack(fill=BOTH, expand=True, padx=10, pady=10) # وضع الإطار في الجزء المتبقي من النافذة.
        self.my_video_label = ttk.Label(self.videos_frame, text="الكاميرا الخاصة بي", bootstyle=INVERSE, anchor=CENTER) # إنشاء ملصق لعرض الفيديو الخاص بالمستخدم.
        self.my_video_label.pack(expand=True) # وضع الملصق في إطار الفيديوهات.
        
        # إطار التحكم السفلي
        control_frame = ttk.Frame(self, padding=10) # إنشاء إطار سفلي لأزرار التحكم العامة.
        control_frame.pack(fill=X) # وضع الإطار أسفل النافذة.
        self.disconnect_button = ttk.Button(control_frame, text="إنهاء الاتصال", command=self.on_closing, bootstyle=DANGER) # إضافة زر "إنهاء الاتصال".
        self.disconnect_button.pack(side=LEFT, padx=5) # وضع الزر على اليسار.
        self.video_button = ttk.Button(control_frame, text="📷 إيقاف الكاميرا", command=self.toggle_video, bootstyle=WARNING) # إضافة زر التحكم بالكاميرا.
        self.video_button.pack(side=RIGHT, padx=5) # وضع الزر على اليمين.
        self.mute_button = ttk.Button(control_frame, text="🎤 كتم الصوت", command=self.toggle_mute, bootstyle=WARNING) # إضافة زر التحكم بالصوت.
        self.mute_button.pack(side=RIGHT, padx=5) # وضع الزر على اليمين.

    def admin_action(self, action): # دالة لتنفيذ إجراءات المشرف.
        if not hasattr(self, 'clients_tree') or not self.clients_tree: # التحقق من وجود قائمة العملاء.
            messagebox.showwarning("تنبيه", "لا توجد قائمة عملاء متاحة") # عرض تحذير إذا لم تكن موجودة.
            return # الخروج من الدالة.
            
        selected_item = self.clients_tree.focus() # الحصول على العنصر (المشارك) الذي حدده المشرف في القائمة.
        if not selected_item: # التحقق من أن المشرف قد حدد عنصراً.
            messagebox.showwarning("تنبيه", "الرجاء تحديد مشارك من القائمة أولاً.") # عرض تحذير إذا لم يحدد شيئاً.
            return # الخروج من الدالة.
        
        item_details = self.clients_tree.item(selected_item) # الحصول على تفاصيل العنصر المحدد.
        # استعادة العنوان من النص
        target_addr_str = item_details['values'][1] # استخراج نص العنوان من تفاصيل العنصر.
        try: # محاولة تحويل النص إلى عنوان (tuple).
            ip, port = target_addr_str.strip("()").replace("'", "").split(', ') # تنظيف النص وتقسيمه للحصول على IP والمنفذ.
            target_addr = (ip, int(port)) # إنشاء العنوان كـ tuple.

            message = {'command': action, 'target_addr': target_addr} # إنشاء رسالة التحكم التي سيتم إرسالها إلى الخادم.
            self.control_socket.sendto(pickle.dumps(message), (self.server_ip, self.control_port)) # إرسال الرسالة إلى الخادم ليقوم بتوجيه الأمر للمشارك المستهدف.
        except Exception as e: # في حال حدوث خطأ.
            messagebox.showerror("خطأ", f"فشل في تنفيذ الإجراء: {e}") # عرض رسالة خطأ.

    def send_video(self, server_ip): # دالة تعمل في خيط منفصل لإرسال الفيديو.
        while self.is_running: # حلقة تستمر طالما أن الاتصال قائم.
            if not hasattr(self, 'cap') or not self.cap.isOpened(): # التحقق من أن الكاميرا تعمل.
                time.sleep(0.1) # الانتظار قليلاً قبل المحاولة مرة أخرى.
                continue # الانتقال إلى الدورة التالية من الحلقة.

            ret, frame = self.cap.read() # قراءة إطار (صورة) واحدة من الكاميرا.
            if not ret: continue # إذا فشلت القراءة، انتقل إلى الدورة التالية.
            
            # عرض الفيديو الخاص بي محلياً
            try: # محاولة عرض الفيديو على واجهة المستخدم.
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # تحويل ألوان الإطار من BGR (الافتراضي في OpenCV) إلى RGB (المناسب لـ Tkinter).
                img = Image.fromarray(frame_rgb) # إنشاء كائن صورة من مصفوفة الإطار.
                img_tk = ImageTk.PhotoImage(image=img.resize((200, 150))) # تحويل الصورة إلى صيغة متوافقة مع Tkinter مع تغيير حجمها.
                self.my_video_label.imgtk = img_tk # الاحتفاظ بمرجع للصورة لمنعها من الحذف بواسطة جامع القمامة في بايثون.
                self.my_video_label.configure(image=img_tk) # تحديث الملصق لعرض الصورة الجديدة.
            except: pass # تجاهل الأخطاء التي قد تحدث أثناء إغلاق البرنامج.

            if self.is_video_off: # إذا كانت الكاميرا في وضع الإيقاف.
                # إرسال إطار أسود إذا كانت الكاميرا متوقفة
                frame = np.zeros((480, 640, 3), dtype=np.uint8) # إنشاء إطار أسود بنفس الأبعاد.
            
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), IMAGE_QUALITY] # إعدادات ضغط الصورة (الجودة).
            _, buffer = cv2.imencode('.jpg', frame, encode_param) # ضغط الإطار بصيغة JPEG لتحويله إلى بايتات.
            
            if buffer is not None: # التحقق من نجاح عملية الضغط.
                self.sockets['video'].sendto(buffer, (server_ip, self.video_port)) # إرسال الإطار المضغوط إلى الخادم.
            time.sleep(0.03) # الانتظار لمدة قصيرة للتحكم في معدل الإطارات (حوالي 30 إطاراً في الثانية).

    def receive_video(self): # دالة تعمل في خيط منفصل لاستقبال الفيديو.
        # وضع ملصق الفيديو الخاص بي في الشبكة
        self.remote_video_labels['me'] = self.my_video_label # إضافة ملصق الفيديو الخاص بالمستخدم إلى قاموس الملصقات.
        self.update_video_grid() # تحديث ترتيب شبكة عرض الفيديو.
        
        while self.is_running: # حلقة تستمر طالما أن الاتصال قائم.
            try: # محاولة استقبال وعرض الفيديو.
                packet, sender_addr = self.sockets['video'].recvfrom(65536) # انتظار واستقبال حزمة بيانات فيديو.
                if not self.is_running: continue # إذا توقف الاتصال، تجاهل الحزمة.

                buffer = packet # تسمية الحزمة بـ buffer.
                frame = cv2.imdecode(np.frombuffer(buffer, dtype=np.uint8), cv2.IMREAD_COLOR) # فك ضغط الصورة (JPEG) وتحويلها مرة أخرى إلى إطار (مصفوفة).
                if frame is None: continue # إذا فشل فك الضغط، تجاهل الحزمة.
                
                addr_key = str(sender_addr) # تحويل عنوان المرسل إلى نص لاستخدامه كمفتاح في القاموس.
                if addr_key not in self.remote_video_labels: # إذا كان هذا الفيديو من مشارك جديد.
                    label = ttk.Label(self.videos_frame, bootstyle=INVERSE, anchor=CENTER) # إنشاء ملصق جديد لعرض الفيديو.
                    self.remote_video_labels[addr_key] = label # إضافة الملصق الجديد إلى القاموس.
                    self.update_video_grid() # إعادة ترتيب شبكة عرض الفيديو لاستيعاب المشارك الجديد.

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # تحويل ألوان الإطار إلى RGB.
                img = Image.fromarray(frame_rgb) # إنشاء كائن صورة.
                
                # تحديث الصورة في الواجهة
                label = self.remote_video_labels[addr_key] # الحصول على الملصق المخصص لهذا المشارك.
                w, h = label.winfo_width(), label.winfo_height() # الحصول على الأبعاد الحالية للملصق في الواجهة.
                if w > 1 and h > 1: # التأكد من أن للملصق أبعاداً فعلية (أكبر من 1 بكسل).
                    img_tk = ImageTk.PhotoImage(image=img.resize((w, h))) # تغيير حجم الصورة لتناسب أبعاد الملصق وتحويلها لصيغة Tkinter.
                    label.imgtk = img_tk # الاحتفاظ بمرجع للصورة.
                    label.configure(image=img_tk) # تحديث الملصق لعرض الصورة الجديدة.

            except Exception as e: # في حال حدوث أي خطأ.
                # print(f"خطأ استقبال فيديو: {e}") # يمكن إلغاء التعليق لطباعة الأخطاء.
                continue # الاستمرار في الحلقة.

    def send_audio(self, server_ip): # دالة تعمل في خيط منفصل لإرسال الصوت.
        while self.is_running: # حلقة تستمر طالما أن الاتصال قائم.
            try: # محاولة قراءة وإرسال الصوت.
                if not self.is_muted: # التحقق من أن المستخدم ليس في وضع الكتم.
                    audio_data = self.audio_stream_in.read(self.chunk_size) # قراءة قطعة من البيانات الصوتية من الميكروفون.
                    self.sockets['audio'].sendto(audio_data, (server_ip, self.audio_port)) # إرسال البيانات الصوتية إلى الخادم.
            except Exception: # في حال حدوث خطأ (مثل إغلاق مجرى الصوت).
                break # الخروج من الحلقة.

    def receive_audio(self): # دالة تعمل في خيط منفصل لاستقبال الصوت.
        while self.is_running: # حلقة تستمر طالما أن الاتصال قائم.
            try: # محاولة استقبال وتشغيل الصوت.
                audio_data, _ = self.sockets['audio'].recvfrom(self.chunk_size * 2) # انتظار واستقبال قطعة من البيانات الصوتية.
                if self.is_running: # التأكد من أن الاتصال لا يزال قائماً بعد استقبال البيانات.
                    self.audio_stream_out.write(audio_data) # كتابة (تشغيل) البيانات الصوتية المستلمة على السماعات.
            except Exception: # في حال حدوث أي خطأ.
                continue # الاستمرار في الحلقة.

    def receive_control(self): # دالة تعمل في خيط منفصل لاستقبال رسائل التحكم.
        while self.is_running: # حلقة تستمر طالما أن الاتصال قائم.
            try: # محاولة استقبال ومعالجة الرسائل.
                data, _ = self.sockets['control'].recvfrom(65536) # انتظار واستقبال رسالة تحكم.
                message = pickle.loads(data) # فك "تغليف" الرسالة.
                command = message.get('command') # الحصول على نوع الأمر.
                
                # أوامر يتلقاها المشرف
                if self.is_admin and command == 'update_list': # إذا كان المستخدم هو المشرف والأمر هو تحديث القائمة.
                    self.update_admin_client_list(message.get('clients', {})) # استدعاء دالة لتحديث عرض قائمة العملاء.
                
                # أوامر يتلقاها العميل العادي
                elif command == 'force_mute': # إذا كان الأمر هو "كتم إجباري".
                    self.is_muted = message.get('status', False) # تحديث حالة الكتم بناءً على الرسالة.
                    self.update_mute_button_status() # تحديث شكل زر الكتم ليعكس الحالة الجديدة.
                    
                    # إرسال حالة الكتم للخادم (لإرسال إشعار للجميع)
                    mute_message = { # إنشاء رسالة لإعلام الخادم بالحالة الجديدة.
                        'command': 'mute_status', 
                        'status': self.is_muted
                    }
                    self.control_socket.sendto(pickle.dumps(mute_message), (self.server_ip, self.control_port)) # إرسال الرسالة.
                    
                elif command == 'force_video_off': # إذا كان الأمر هو "إيقاف كاميرا إجباري".
                    self.is_video_off = message.get('status', False) # تحديث حالة الكاميرا.
                    self.update_video_button_status() # تحديث شكل زر الكاميرا.
                elif command == 'kick': # إذا كان الأمر هو "طرد".
                    messagebox.showinfo("تم الطرد", "قام المشرف بطردك من الجلسة.") # عرض رسالة للمستخدم.
                    self.on_closing(force=True) # إغلاق البرنامج بشكل إجباري.
                elif command == 'server_shutdown': # إذا كان الأمر هو "إغلاق الخادم".
                    messagebox.showinfo("انقطاع", "أغلق المشرف الجلسة.") # عرض رسالة للمستخدم.
                    self.on_closing(force=True) # إغلاق البرنامج بشكل إجباري.
                elif command == 'notification': # إذا كان الأمر هو "إشعار".
                    # إضافة الإشعار إلى الطابور لعرضه في الواجهة
                    self.notification_queue.put(message.get('message', '')) # وضع رسالة الإشعار في الطابور ليتم عرضها لاحقاً.

            except Exception: # في حال حدوث أي خطأ.
                continue # الاستمرار في الحلقة.

    def update_admin_client_list(self, clients): # دالة لتحديث قائمة المشاركين في واجهة المشرف.
        # مسح القائمة الحالية
        for i in self.clients_tree.get_children(): # حلقة تكرارية على جميع العناصر الموجودة في القائمة.
            self.clients_tree.delete(i) # حذف العنصر.
        # إضافة العملاء الجدد
        for addr_str, info in clients.items(): # حلقة تكرارية على قاموس العملاء الجديد.
            # إضافة سطر جديد إلى القائمة بالاسم والعنوان.
            self.clients_tree.insert('', 'end', values=(info['name'], addr_str))

    def update_video_grid(self): # دالة لترتيب نوافذ الفيديو في شبكة.
        # إزالة الملصقات القديمة من الترتيب
        for widget in self.videos_frame.winfo_children(): # حلقة تكرارية على كل العناصر داخل إطار الفيديو.
            widget.place_forget() # إزالة التموضع الحالي للعنصر (دون حذفه).
            
        labels = list(self.remote_video_labels.values()) # الحصول على قائمة بجميع ملصقات الفيديو.
        num_videos = len(labels) # حساب عدد الفيديوهات.
        if num_videos == 0: return # إذا لم يكن هناك فيديوهات، اخرج من الدالة.

        cols = int(np.ceil(np.sqrt(num_videos))) # حساب العدد الأمثل للأعمدة (الجذر التربيعي للعدد الإجمالي).
        rows = int(np.ceil(num_videos / cols)) if cols > 0 else 0 # حساب عدد الصفوف اللازمة.
        
        for i, label in enumerate(labels): # حلقة تكرارية على كل ملصق فيديو مع الحصول على ترتيبه (i).
            row, col = divmod(i, cols) # حساب رقم الصف والعمود الحالي بناءً على الترتيب.
            label.place(relx=col/cols, rely=row/rows, relwidth=1/cols, relheight=1/rows) # وضع الملصق في الشبكة باستخدام الإحداثيات النسبية لضمان توزيع متساوٍ.

    def toggle_mute(self): # دالة يتم استدعاؤها عند الضغط على زر كتم الصوت.
        self.is_muted = not self.is_muted # عكس قيمة متغير حالة الكتم (من True إلى False والعكس).
        self.update_mute_button_status() # تحديث شكل الزر.
        
        # إرسال حالة الكتم للخادم
        mute_message = { # إنشاء رسالة لإعلام الخادم بالحالة الجديدة.
            'command': 'mute_status', 
            'status': self.is_muted
        }
        self.control_socket.sendto(pickle.dumps(mute_message), (self.server_ip, self.control_port)) # إرسال الرسالة.
    
    def update_mute_button_status(self): # دالة لتحديث نص ولون زر كتم الصوت.
        if self.is_muted: # إذا كان المستخدم في وضع الكتم.
            self.mute_button.config(text="🎤 إلغاء الكتم", bootstyle=SUCCESS) # تغيير النص واللون للإشارة إلى أن الضغطة التالية ستلغي الكتم.
        else: # إذا لم يكن في وضع الكتم.
            self.mute_button.config(text="🔇 كتم الصوت", bootstyle=WARNING) # تغيير النص واللون للإشارة إلى أن الضغطة التالية ستفعل الكتم.

    def toggle_video(self): # دالة يتم استدعاؤها عند الضغط على زر الكاميرا.
        self.is_video_off = not self.is_video_off # عكس قيمة متغير حالة الكاميرا.
        self.update_video_button_status() # تحديث شكل الزر.

    def update_video_button_status(self): # دالة لتحديث نص ولون زر الكاميرا.
        if self.is_video_off: # إذا كانت الكاميرا متوقفة.
            self.video_button.config(text="📷 تشغيل الكاميرا", bootstyle=SUCCESS) # تغيير النص واللون للإشارة إلى أن الضغطة التالية ستشغل الكاميرا.
        else: # إذا كانت الكاميرا تعمل.
            self.video_button.config(text="📷 إيقاف الكاميرا", bootstyle=WARNING) # تغيير النص واللون للإشارة إلى أن الضغطة التالية ستوقف الكاميرا.

    def on_closing(self, force=False): # دالة يتم استدعاؤها عند محاولة إغلاق البرنامج.
        confirm = force or messagebox.askokcancel("خروج", "هل أنت متأكد أنك تريد إنهاء الاتصال؟") # عرض مربع حوار للتأكيد، إلا إذا كان الإغلاق إجبارياً (force=True).
        if confirm: # إذا وافق المستخدم على الخروج.
            self.is_running = False # تعيين حالة التشغيل إلى False لإيقاف جميع الحلقات التكرارية في الخيوط.
            time.sleep(0.5) # الانتظار لمدة نصف ثانية لإعطاء فرصة للخيوط للتوقف بشكل سليم.

            if not self.is_admin and hasattr(self, 'server_ip'): # إذا كان المستخدم عميلاً عادياً (وليس المشرف).
                leave_message = {'command': 'leave'} # إنشاء رسالة مغادرة.
                self.sockets['control'].sendto(pickle.dumps(leave_message), (self.server_ip, self.control_port)) # إرسال رسالة المغادرة إلى الخادم.
            
            if self.server: # إذا كان المستخدم هو المشرف (وبالتالي يمتلك كائن الخادم).
                self.server.stop() # إيقاف الخادم.
            
            # إغلاق الموارد
            if hasattr(self, 'cap'): # التحقق من وجود كائن الكاميرا.
                self.cap.release() # تحرير الكاميرا.
            if hasattr(self, 'p_audio'): # التحقق من وجود كائن الصوت.
                self.p_audio.terminate() # إنهاء خدمة الصوت.
            if hasattr(self, 'sockets'): # التحقق من وجود قاموس المقابس.
                for s in self.sockets.values(): # حلقة تكرارية على جميع المقابس.
                    s.close() # إغلاق كل مقبس.
            
            self.destroy() # تدمير نافذة الواجهة الرسومية.
            sys.exit(0) # إنهاء البرنامج بشكل كامل.

if __name__ == "__main__": # نقطة بداية تنفيذ البرنامج. هذا الشرط يضمن أن الكود التالي لا يعمل إلا عند تشغيل الملف مباشرة.
    app = ChatApp() # إنشاء كائن من فئة التطبيق الرئيسية.
    app.mainloop() # بدء الحلقة الرئيسية للواجهة الرسومية، والتي تجعل البرنامج ينتظر تفاعل المستخدم.