# import os
# import png
# import torch
# import torchvision
# import numpy as np
# import boto3
# import requests
# from cv2 import (
#     imread, cvtColor, COLOR_BGR2RGB, threshold,
#     THRESH_BINARY, THRESH_BINARY_INV
# )
# from PIL import Image
# from typing import List, Optional
# from celery import Task

# from django.conf import settings

# from .data_loader import (
#     RescaleT, ToTensorLab, SalObjDataset, DataLoader
# )
# from .model import U2NET, U2NETP


# class BG_REMOVAL_MODEL_OPTION:
#     u2net = 'u2net'
#     u2netp = 'u2netp'

#     __MODEL_MAP = {
#         u2net: U2NET(3, 1),
#         u2netp: U2NETP(3, 1)
#     }

#     @classmethod
#     def get_model(cls, model_name: str):
#         if model_name not in cls.__MODEL_MAP:
#             raise Exception("Invalid model")
#         return cls.__MODEL_MAP[model_name]


# class BackgroundRemovalUtil:
#     MODEL_NAME: str = 'u2net'
#     MODEL_DIR = os.path.join(settings.DATA_STORAGE_PATH, 'models')
#     TMP_DIR = os.path.join(settings.DATA_STORAGE_PATH, 'tmp')
#     RESULTS_TEST_DIR = os.path.join(TMP_DIR, 'bg_removal_tests')
#     RESULTS_DIR = os.path.join(TMP_DIR, 'bg_removal_results')

#     MODEL_STORAGE_BUCKET_PATH = settings.AWS_STORAGE_BUCKET_NAME +\
#         '/models/u2net.pth'

#     __net: torch.nn.Module = U2NET
#     __task: Optional[Task] = None

#     def __init__(
#         self, task: Task = None,
#         model_name: str = BG_REMOVAL_MODEL_OPTION.u2net,
#         load_model: bool = True
#     ):
#         self.__task = task
#         if load_model:
#             self.net = model_name
#         else:
#             self.MODEL_NAME = model_name

#     @property
#     def __model_file_name(self) -> str:
#         return os.path.join(self.MODEL_DIR, f'{self.MODEL_NAME}.pth')

#     @property
#     def task(self) -> Optional[Task]:
#         return self.__task

#     @property
#     def is_model_file_ready(self) -> bool:
#         return os.path.isfile(self.__model_file_name)

#     def log(self, msg: str):
#         if isinstance(self.task, Task) and not self.task.abstract:
#             self.task.update_state(state='IN PROGRESS', meta={'msg': msg})
#         else:
#             print(msg)

#     def download_model(self, path: str = None):
#         if not path:
#             path = self.MODEL_STORAGE_BUCKET_PATH
#         bucket_name, *path_segs = self.MODEL_STORAGE_BUCKET_PATH.split('/')
#         s3_path_key = '/'.join(path_segs)
#         model_file_name = os.path.basename(self.MODEL_STORAGE_BUCKET_PATH)
#         s3 = boto3.resource(
#             's3',
#             aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
#             aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY)
#         s3.Bucket(bucket_name).download_file(
#             s3_path_key, os.path.join(self.MODEL_DIR, model_file_name))

#     @property
#     def net(self) -> torch.nn.Module:
#         return self.__net

#     @net.setter
#     def net(self, model_name: str):
#         if model_name not in [
#             BG_REMOVAL_MODEL_OPTION.u2net,
#             BG_REMOVAL_MODEL_OPTION.u2netp
#         ]:
#             raise Exception(f'Unknown model name - `{model_name}`!')

#         self.MODEL_NAME = model_name
#         self.__net = BG_REMOVAL_MODEL_OPTION.get_model(model_name)
#         self.__load_model()

#     def __load_model(self):
#         self.__net.load_state_dict(torch.load(
#             self.__model_file_name, map_location=torch.device('cpu')))

#     def __download_images_from_urls(self, urls: List[str]) -> List[str]:
#         file_paths = []
#         for url in urls:
#             self.log(f"Downloading {url}")
#             filename = os.path.basename(url)
#             input_image_filepath = os.path.join(
#                 settings.DATA_STORAGE_PATH, filename)
#             img_data = requests.get(url).content
#             with open(input_image_filepath, 'wb') as handler:
#                 handler.write(img_data)

#             file_paths.append(input_image_filepath)
#         return file_paths

#     def run(
#         self,
#         image_file_paths: List[str] = None,
#         image_urls: List[str] = None,
#         model_name: str = BG_REMOVAL_MODEL_OPTION.u2net,
#         save_predict: bool = False,
#         resize: bool = False
#     ) -> List[str]:
#         if not image_file_paths and not image_urls:
#             return []

#         if self.MODEL_NAME != model_name:
#             self.net = model_name

#         if not isinstance(image_urls, list):
#             image_urls = list()
#         if not isinstance(image_file_paths, list):
#             image_file_paths = list()

#         downloaded_files = self.__download_images_from_urls(image_urls)
#         image_file_paths += downloaded_files

#         if resize:
#             for image_file_path in image_file_paths:
#                 # resized_file_pathname = os.path.join(
#                 #     settings.DATA_BG_REMOVAL_SOURCE_PATH,
#                 #     f"{uuid4()}--{data.name}"
#                 # )
#                 image = Image.open(image_file_path)
#                 resized_image = image.resize((
#                     settings.LISTING_ITEM_IMAGE_RESIZE_DEFAULT_WIDTH,
#                     settings.LISTING_ITEM_IMAGE_RESIZE_DEFAULT_HEIGHT
#                 ))
#                 resized_image.save(image_file_path)

#         test_salobj_dataset = SalObjDataset(
#             img_name_list=image_file_paths, lbl_name_list=[],
#             transform=torchvision.transforms.Compose([
#                 RescaleT(320), ToTensorLab(flag=0)]))

#         test_salobj_dataloader = DataLoader(
#             test_salobj_dataset, batch_size=1,
#             shuffle=False, num_workers=0)

#         result_file_paths = []

#         for idx, data_test in enumerate(test_salobj_dataloader):
#             file_pathname = image_file_paths[idx]
#             file_name, _ = os.path.splitext(
#                 os.path.basename(image_file_paths[idx]))
#             self.log(f'inferencing: {file_pathname}')

#             inputs_test = data_test['image'].type(torch.FloatTensor)

#             if torch.cuda.is_available():
#                 inputs_test = torch.autograd.Variable(inputs_test.cuda())
#             else:
#                 inputs_test = torch.autograd.Variable(inputs_test)

#             d1 = self.net(inputs_test)[0]

#             # normalization
#             pred = d1[:, 0, :, :]
#             ma = torch.max(pred)
#             mi = torch.min(pred)
#             pred = (pred-mi)/(ma-mi)

#             img_original = cvtColor(imread(file_pathname), COLOR_BGR2RGB)
#             predict_np = pred.squeeze().cpu().data.numpy()
#             predict_image = Image.fromarray(predict_np*255).convert('RGB')
#             resized_predict_image = predict_image.resize(
#                 (img_original.shape[1], img_original.shape[0]),
#                 resample=Image.BILINEAR)

#             if save_predict:
#                 temp_filename = os.path.join(
#                     self.RESULTS_TEST_DIR, f'{file_name}.png')
#                 resized_predict_image.save(temp_filename)

#             converted_predict_image = cvtColor(
#                 np.array(resized_predict_image), COLOR_BGR2RGB)

#             ret, thresh1 = threshold(
#                 converted_predict_image, 127, 1, THRESH_BINARY)
#             ret, thresh2 = threshold(
#                 converted_predict_image, 127, 255, THRESH_BINARY_INV)

#             result = img_original * thresh1 + thresh2
#             result = result.tolist()

#             rows, cols = thresh1.shape[:2]
#             for i in range(rows):
#                 for j in range(cols):
#                     if thresh1[i][j][0] == 0:
#                         result[i][j].append(0)
#                     else:
#                         result[i][j].append(255)

#             result = np.reshape(result, (rows, cols * 4))
#             rlt = result.astype('uint8')
#             bg_removed_file_pathname = os.path.join(
#                 self.RESULTS_DIR, f'{file_name}.png')
#             png.from_array(rlt, mode='RGBA').save(
#                 bg_removed_file_pathname)

#             del d1
#             result_file_paths.append(bg_removed_file_pathname)

#         # NOTE: Delete the downloaded files from url
#         for file_to_delete in downloaded_files:
#             os.remove(file_to_delete)
#         return result_file_paths
