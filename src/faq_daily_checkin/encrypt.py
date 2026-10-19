"""
访问 https://idas.uestc.edu.cn/authserver/login，服务端会马上把源码发给客户端，
包括 encrypt.js，用于给表单中的密码加密之后再POST.

问题是我刚访问页面你就把加密逻辑扔给我了，那这种加密有什么意义？

本文件是 encrypt.js 的 python 等价实现:
1. 如果加密密钥 f 为空，直接返回原始密码 n。
2. 如果密钥不为空，生成一个长度为 64 的随机字符串，拼接在密码前面。
3. 将密钥和长度为 16 的随机字符串分别作为 AES 密钥和 IV。
4. 使用 AES-CBC 模式和 PKCS#7 填充加密。
5. 输出 Base64 编码的密文。
6. 如果加密过程中发生异常，encryptPassword 会捕获异常并返回原始密码。

由于 AES CBC 的特性, 第 N 块密文的原始文本 = 第 N 块解密之后的数据块与 N-1 密文块异或
所以无需知道 IV 和密码前的随机字符串也可以实现解密.

encrypt_password 用于加密密码，发给登录接口，实现自动化登录.
需要的 salt 包含在该html页面的隐藏元素中:
    <input type="hidden" id="pwdEncryptSalt" value="salt">
"""

import base64
import random

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

CHARSET = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"


def get_random_string(length: int) -> str:
    return "".join(random.choice(CHARSET) for _ in range(length))


def encrypt_password(password: str, salt: str) -> str:
    """同 encrypt.js 加密逻辑"""
    if not salt or len(salt) != 16:
        raise ValueError("Salt 必须是 16 个字符")

    random_prefix = get_random_string(64)
    plain_text = (random_prefix + password).encode("utf-8")

    key = salt.encode("utf-8")
    iv = get_random_string(16).encode("utf-8")

    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(plain_text, AES.block_size, style="pkcs7")
    ciphertext = cipher.encrypt(padded_data)

    return base64.b64encode(ciphertext).decode("utf-8")


def decrypt_password(ciphertext_b64: str, salt: str) -> str:
    """
    解密金智 CAS 系统的 AES 密文，提取出原始密码
    仅用于测试加密函数是否有效。

    :param ciphertext_b64: Base64 编码的密文字符串
    :param salt: 16 字符的 pwdEncryptSalt (作为 AES Key)
    :return: 提取出的原始密码明文
    """
    if not salt or len(salt) != 16:
        raise ValueError("Salt 必须是 16 个字符")

    try:
        # 1. Base64 解码
        ciphertext_bytes = base64.b64decode(ciphertext_b64)
    except ValueError as e:
        raise ValueError(f"Base64 解码失败: {e}")

    # 2. 准备 Key 和任意 IV
    key = salt.encode("utf-8")

    # 因为真实密码在第 5 个 Block (索引 4) 开始，
    # CBC 模式下解密 Block N 只需要 Block N 和 Block N-1 的密文，不依赖 IV。
    # 所以 IV 是什么根本无所谓，这里随便给 16 个 0 即可。
    # 参考 https://en.wikipedia.org/wiki/Block_cipher_mode_of_operation#Cipher_block_chaining_(CBC)
    fake_iv = b"0000000000000000"

    # 3. 创建 AES 解密器并执行解密
    cipher = AES.new(key, AES.MODE_CBC, fake_iv)

    try:
        decrypted_padded = cipher.decrypt(ciphertext_bytes)
        # 4. 去除 PKCS7 填充
        decrypted_bytes = unpad(decrypted_padded, AES.block_size)
    except ValueError:
        raise ValueError("解密失败：密文被篡改、Key 错误，或填充格式不正确")

    # 5. 提取真实密码
    # 明文结构是：[ 64字节随机前缀 ] + [ 真实密码 ]
    # 我们只需要把前 64 个字节砍掉，剩下的就是真实密码
    if len(decrypted_bytes) < 64:
        raise ValueError("解密后的数据长度不足 64 字节，不符合 CAS 加密规范")

    password_bytes = decrypted_bytes[64:]

    # 6. 解码为字符串
    try:
        return password_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(
            "提取出的密码包含非法的 UTF-8 字符，可能是 Key 错误导致解密出乱码"
        )
