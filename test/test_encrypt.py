from faq_daily_checkin.encrypt import decrypt_password, encrypt_password


def test_decrypt():
    # 测试加密函数的有效性
    salt = "SR1ZPsX5BpZtTdrZ"
    real_password = "123456"
    # 抓包得到的密文
    real_enc = "sa5m49POWK6fMVc9nYY9PwQztpFl25hyZ7vtgCuHWycQ24kHyT3+0jrlCA9ZstaU9eq4XjIOvVZaFqsUH97yZCE9FeMrjNyBjAoPlR3TDn0="
    my_password = decrypt_password(real_enc, salt)
    assert my_password == real_password


def test_encrypt():
    # 测试解密函数有效性
    salt = "SR1ZPsX5BpZtTdrZ"
    password = "123456"
    my_enc = encrypt_password(password, salt)
    dec = decrypt_password(my_enc, salt)
    assert dec == password
