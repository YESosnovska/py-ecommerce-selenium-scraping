import csv
import dataclasses
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import Tag, BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By


BASE_URL = "https://webscraper.io/"
HOME_URL = urljoin(BASE_URL, "test-sites/e-commerce/more/")
COMPUTERS_URL = urljoin(HOME_URL, "computers/")
LAPTOPS_URL = urljoin(COMPUTERS_URL, "laptops/")
TABLETS_URL = urljoin(COMPUTERS_URL, "tablets/")
PHONES_URL = urljoin(HOME_URL, "phones/")
TOUCH_URL = urljoin(PHONES_URL, "touch/")

_driver: WebDriver | None = None


def get_driver() -> WebDriver:
    return _driver


def set_driver(new_driver: WebDriver) -> None:
    global _driver
    _driver = new_driver


@dataclass
class Product:
    title: str
    description: str
    price: float
    rating: int
    num_of_reviews: int
    additional_info: dict | None = None


PRODUCT_FIELDS = [field.name for field in dataclasses.fields(Product)]


def parse_hdd_block_price(product_soup: Tag) -> dict[str, float]:
    absolute_url = urljoin(BASE_URL, product_soup.select_one(".title")["href"])
    driver = get_driver()
    driver.get(absolute_url)
    swatches = driver.find_element(By.CLASS_NAME, "swatches")
    buttons = swatches.find_elements(By.TAG_NAME, "button")

    prices = {}
    for button in buttons:
        if not button.get_property("disabled"):
            button.click()
            prices[button.get_property("value")] = float(
                driver.find_element(
                    By.CLASS_NAME, "price"
                ).text.replace(
                    "$", "")
            )

    return prices


def parse_single_product(product: Tag) -> Product:
    parsed_product = Product(
        title=product.select_one(".title")["title"],
        description=product.select_one(".description").text,
        price=float(product.select_one(".price").text.replace("$", "")),
        rating=int(product.select_one("p[data-rating]")["data-rating"]),
        num_of_reviews=int(
            product.select_one(".review-count").text.split()[0]
        ),
    )

    if product.select_one(".swatches"):
        hdd_prices = parse_hdd_block_price(product)
        parsed_product.additional_info = {"hdd_prices": hdd_prices}

    return parsed_product


def get_home_products() -> [Product]:
    text = requests.get(HOME_URL).content
    soup = BeautifulSoup(text, "html.parser")
    products = soup.select(".product-wrapper.card-body")
    return [parse_single_product(product) for product in products]


def get_page_products(page_url: str) -> [Product]:
    text = requests.get(page_url).content
    page_soup = BeautifulSoup(text, "html.parser")
    driver = get_driver()
    driver.get(page_url)

    if driver.find_element(By.CLASS_NAME, "btn.btn-lg"):
        button = driver.find_element(By.CLASS_NAME, "btn.btn-lg")
        while True:
            button.click()

    products = page_soup.select(".product-wrapper.card-body")
    return [parse_single_product(product) for product in products]


def write_products_to_csv(products: [Product], file_name: str) -> None:
    with open(file_name, "w") as f:
        writer = csv.writer(f)
        writer.writerow(PRODUCT_FIELDS)
        writer.writerows(
            [dataclasses.astuple(product) for product in products]
        )


def get_all_products() -> None:
    with webdriver.Chrome() as driver:
        set_driver(driver)
        write_products_to_csv(get_home_products(), "home.csv")
        write_products_to_csv(get_page_products(
            COMPUTERS_URL), "computers.csv"
        )
        write_products_to_csv(get_page_products(LAPTOPS_URL), "laptops.csv")
        write_products_to_csv(get_page_products(TABLETS_URL), "tablets.csv")
        write_products_to_csv(get_page_products(PHONES_URL), "phones.csv")
        write_products_to_csv(get_page_products(TOUCH_URL), "phones.csv")


if __name__ == "__main__":
    get_all_products()
