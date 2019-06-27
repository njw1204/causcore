import time
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup


h = {
    "Accept": "*/*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
}


def cau_sso_login(session, id, password):
    s = session
    init_data = {
        "userID": id,
        "password": password,
        "credType": "BASIC",
        "retURL": "http://cauid.cau.ac.kr/smssoln_pcs.asp?smlnloginid=" + id
    }

    r = s.post("https://sso2.cau.ac.kr/SSO/AuthWeb/Logon.aspx?ssosite=cauid.cau.ac.kr", data=init_data, headers=h)

    for i in range(2):
        bs = BeautifulSoup(r.text, "html5lib")
        inputs = bs.select("input")
        data = dict()

        for j in inputs:
            try:
                data[j["name"]] = j["value"]
            except: pass

        if i == 0:
            r = s.post("https://sso2.cau.ac.kr/SSO/AuthWeb/LogonDomain.aspx", data=data, headers=h)
        else:
            r = s.post("https://sso2.cau.ac.kr/SSO/AuthWeb/NACookieManage.aspx", data=data, headers=h)

    if init_data["retURL"] not in r.text:
        return False

    s.get(init_data["retURL"], headers=h)
    return True


def get_class_list(session):
    s = session
    r = s.get("http://cauid.cau.ac.kr/Symtra_Attendance/ClassList.asp?code=000300020003", headers=h)
    bs = BeautifulSoup(r.text, "html5lib")
    title_list, url_list = [], []

    strong_class_titles = bs.select(".title .tit")
    for i in strong_class_titles:
        title_list.append(i.text.strip())
    
    a_class_urls = bs.select(".info a")
    for i in a_class_urls:
        url_list.append("http://cauid.cau.ac.kr/Symtra_Attendance/" + i.get("href"))

    return tuple(zip(title_list, url_list))


def get_score_for_class(session, url):
    try:
        s = session
        r = s.get(url, headers=h)
        bs = BeautifulSoup(r.text, "html5lib")
        table = bs.select_one(".tbl_type2")
        if not table:
            return None

        head_list, body_list = [], []
        for i in table.select("thead th"):
            head_list.append(i.text.strip())
        for i in table.select("tbody td"):
            body_list.append(i.text.strip())

        return tuple(zip(head_list, body_list))

    except: return None


if __name__ == "__main__":
    print("[중앙대 성적 자동 알리미]\n")
    print("[중앙대 e-ID 로그인]")
    id = input("id : ")
    pw = input("pw : ")
    s = requests.session()

    print("\n[이메일 알림 설정]")
    print("1 : Gmail")
    print("2 : Naver")
    print("3 : 알림 X")
    select = int(input("선택 = "))
    smtp_host = ""

    if select == 1:
        smtp_host = "smtp.gmail.com"
        mail_hostname = "gmail"
        mail_domain = "gmail.com"
    elif select == 2:
        smtp_host = "smtp.naver.com"
        mail_hostname = "naver"
        mail_domain = "naver.com"

    if smtp_host:
        print("\n[이메일 계정 로그인]")
        e_id = input(mail_hostname + " id : ")
        e_pw = input(mail_hostname + " pw : ")
        smtp_session = smtplib.SMTP_SSL(smtp_host, 465)
        try:
            smtp_session.login(e_id, e_pw)
            smtp_session.quit()
            email = e_id + "@" + mail_domain
            print("\n이메일 계정 로그인 성공!")
        except Exception as e:
            print(e)
            print("\n이메일 계정 로그인 실패. 프로그램을 종료합니다.")
            print("해당 메일 사이트에서 연동 설정을 완료했는지 확인해주세요.")
            exit(1)
    else:
        print()

    start_time = datetime(year=1900, month=1, day=1)
    program_init_time = datetime.now()
    score_dict = dict()
    turn = 1

    while True:
        try:
            if datetime.now() - start_time > timedelta(minutes=3):
                s = requests.session()
                if cau_sso_login(s, id, pw):
                    if turn == 1:
                        print("중앙대 e-ID 로그인 성공!")
                        print("성적 변동 실시간 감시를 시작합니다...")
                        print("=======================================")
                    start_time = datetime.now()
                else:
                    print("\n중앙대 e-ID 로그인 실패.\n")
                    raise Exception("login error")
            x = get_class_list(s)

            for i in range(len(x)):
                score = get_score_for_class(s, x[i][1])
                if not score: continue
                if x[i][0] not in score_dict or score_dict[x[i][0]] != score:
                    head = "[성적 변동] " + x[i][0]
                    output = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for j in score:
                        output += "\n > " + j[0] + " : " + j[1]
                    print("\n" + head + "\n" + output)
                    score_dict[x[i][0]] = score

                    if turn > 1 and smtp_host:
                        for tt in range(3):
                            try:
                                smtp_session = smtplib.SMTP_SSL(smtp_host, 465)
                                smtp_session.login(e_id, e_pw)
                                msg = MIMEText(head + "\n" + output, _charset="utf-8")
                                msg["Subject"] = head
                                msg["From"] = email
                                msg["To"] = email
                                smtp_session.sendmail(email, email, msg.as_string())
                                smtp_session.quit()
                                print("<알림 메일 전송 성공>")
                                break
                            except Exception as e:
                                print(e)
                                print("<알림 메일 전송 실패>")

        except Exception as e:
            print("\n[Unknown Error]")
            print(e)
            print()
        finally:
            time.sleep(30)
            turn += 1
