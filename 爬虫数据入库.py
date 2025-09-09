import requests
from bs4 import BeautifulSoup
import pymysql
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
"""爬取内容为当日（实时）企业基金数据"""
dit = {"referer": "https://www.dayfund.cn/incrank.html"
  ,
       "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0"}
#没找到合适的ip代理
proxies = {
  None
}

#用以暂时存储读取数据
df_list = []

def download_one_page(index, url):
  try:
      req = requests.get(url=url, headers=dit, timeout=(3, 10),verify=False)#timeout用以延长访问间隔
      soup = BeautifulSoup(req.text, "html.parser")
      table = soup.find_all("tr", class_=["row1", "row2"])
      header_row = soup.find('tr', class_='rowh')

      if header_row:
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]# 这步骤可要可不要
      else:
        headers = ['序号', '基金代码', '基金名称', '日增长', '近1周', '近1月', '近1季', '近半年', '今年来', '近1年',
                   '近2年''近3年']  # 根据实际表格列数修改

      for row in table:
        cells = row.find_all('td')
        row_data = [cell.get_text(strip=True) for cell in cells]
        # 如果表头存在且长度匹配，则将行数据与表头组合成字典
        if len(row_data) == len(headers):
          row_dict = dict(zip(headers, row_data))
          df_list.append(row_dict)
        # 如果长度不匹配，可能是不需要的数据或表格结构变化
        else:
           print(f"Row data length mismatch on page {index}: {row_data}")
      print(f"第{index}页爬取完成")
      #设置随机延时，如若频繁请求可能触发网站反爬机制
      time.sleep(random.uniform(1, 3))
  except Exception as en:
          print(f"第{index}页爬取失败: {str(en)}")

def save_to_mysql(data_list):
    if not data_list:
        print("没有数据可保存，数据列表为空")
        return
    conn = None
    cursor = None
    try:
        #连接到自建数据库
        conn = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='liu@423615',
            autocommit=True,
            charset = 'utf8mb4',
            database = 'spider_database'
        )
        cursor = conn.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS dayfund_spider_data (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        `序号` VARCHAR(10),
                        `基金代码` VARCHAR(20),
                        `基金名称` VARCHAR(100),
                        `日增长` VARCHAR(20),
                        `近1周` VARCHAR(20),
                        `近1月` VARCHAR(20),
                        `近1季` VARCHAR(20),
                        `近半年` VARCHAR(20),
                        `今年来` VARCHAR(20),
                        `近1年` VARCHAR(20),
                        `近2年` VARCHAR(20),
                        `近3年` VARCHAR(20),
                        `created_at`TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
                                """
        truncate_table_query = "TRUNCATE TABLE dayfund_spider_data"

        cursor.execute(create_table_query)
        cursor.execute(truncate_table_query)
        insert_query = """
                       INSERT INTO dayfund_spider_data (`序号`, `基金代码`, `基金名称`, `日增长`, `近1周`, `近1月`, `近1季`, `近半年`, `今年来`, `近1年`, `近2年`, `近3年`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       """

        records_to_insert = []
        for item in data_list:
            record = (
                item.get('序号', ''),
                item.get('基金代码', ''),
                item.get('基金名称', ''),
                item.get('日增长', ''),
                item.get('近1周', ''),
                item.get('近1月', ''),
                item.get('近1季', ''),
                item.get('近半年', ''),
                item.get('今年来', ''),
                item.get('近1年', ''),
                item.get('近2年', ''),
                item.get('近3年', '')
            )
            records_to_insert.append(record)
            if records_to_insert:  # 确保有数据可插入（为空则执行else）
                cursor.executemany(insert_query, records_to_insert)
                conn.commit()  # 提交事务
                print(f"成功插入 {len(records_to_insert)} 条记录到spider_database数据库")
            else:
                print("准备插入的记录列表为空，跳过插入操作")

    except pymysql.MySQLError as pe:
            print(f"数据库错误: {str(pe)}")
            if conn:
                conn.rollback()  # 发生错误时可及时回滚
    except Exception as ec:
        print(f"保存数据出错: {str(ec)}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    # 这是爬取页面的范围，这个网页共有116页
    pages = range(1, 6)
    urls = [f"https://www.dayfund.cn/incrank_p{i}.html" for i in pages]

    # 使用线程池以提高运行效率，并确保所有线程完成
    with ThreadPoolExecutor(max_workers=2) as T:#此处max_workers为最大线程数
        # 提交所有任务并获取Future对象
        futures = [T.submit(download_one_page, i, url) for i, url in enumerate(urls)]

        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                future.result()  # 获取结果（如果有异常会在这里抛出）
            except Exception as e:
                print(f"线程执行出错: {str(e)}")

    # 所有线程完成后再保存数据
    print(f"所有页面爬取完成，共获取 {len(df_list)} 条数据，开始写入数据库...")
    #传入读取数据并写入数据库
    save_to_mysql(df_list)

"""后续用异步协程方法改写‘写入数据库函数部分’以提高写入效率"""
"""也可将全部函数框架用异步协程框架改写"""











