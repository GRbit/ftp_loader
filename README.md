# FTP loader

Для работы с ftp используется [ftput](https://github.com/GRbit/ftput/)

###Установка:
```
git clone https://github.com/GRbit/ftp_loader
cd ftp_loader
git submodule update --init --recursive
```
###Логика работы
В начале загрузки создаёт файл для записи логов, пишет туда даные об отдельных файлах, успешно ли он был передан. После первого прохода проверяет всё ли передано, если нет, передаёт что не передано по новой, это считается второй поыткой (см tries в опциях). Пытается скачать снова пока не кончится лимит попыток повторного скачивания. 

Полный листинг файлов в начале передачи папки не составляется, проходит по всем папкам и подпапкам в порядке выданном сервером при отправке команды NLST.

Передача симлинков не поддерживается, рекурсивные симлинки приводят к бесконечной рекурсии =)
###Использование:
Для передачи файлов нужно указать куда их передавать через опцию -t и откуда скачивать через опцию -f. Одна из опций должна быть путём к существующей папке или  к файлу в существующей папке, другая же строкой типа ftp connection.

Вид ftp connection:
```
ftp://[YourFtpUser[:YourFtpUserPassword]@]yourdomain.com[:port][/path]
```

Пример передачи файла
```
[0] $ python3 loader.py -t tst.py -f ftp://grbit_tstt:tsttst6@zorro/fлво.py 
...
[0] $ ll tst.py
-rw-rw-r-- 1 grbit grbit 7,4K марта 14 13:39 tst.py
```
Пример передачи папки
```
[0] $ python3 loader.py -t . -f ftp://grbit_tstt:tsttst6@zorro/dir1
...
[0] $ ll dir1/
total 5,8M
-rw-rw-r-- 1 grbit grbit 1,2M марта 14 13:41 1
-rw-rw-r-- 1 grbit grbit 3,5M марта 14 13:41 2
-rw-rw-r-- 1 grbit grbit  625 марта 14 13:41 3
...
```
###Опции:
- debug/d NUM

Включить более подробный вывод. 1 - вывод операций с файлами, 2 - полный листинг связи с сервером по FTP.
По умолчанию debug=0
- overwrite/o

Если включено, то перезаписывает уже присутствующие в точке назанчения файлы. Если не отмечено, то спросит о том что с ними делать.
- logfile/l

Указать файл в который будет записываться лог. По умолчанию файл создаётся из хэша места отправления, назначения и директории запуска. По умолчанию файл с логом удаляется после успешного завершения передачи (после зароса подтверждения)
- resume/r BOOL

По умолчанию включено. Продолжить передачу файлов используя файл с логом.
- tries Num

Количество попыток повторной передаче файлов. По умолчанию 5.