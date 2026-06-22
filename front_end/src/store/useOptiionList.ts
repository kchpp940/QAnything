/*
 * @Author: 祝占朋 wb.zhuzp01@rd.netease.com
 * @Date: 2023-11-01 14:57:33
 * @LastEditors: Ianarua 306781523@qq.com
 * @LastEditTime: 2024-08-06 10:25:59
 * @FilePath: front_end/src/store/useOptiionList.ts
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */

import { formatFileSize } from '@/utils/utils';
import { message } from 'ant-design-vue';
import { useKnowledgeBase } from '@/store/useKnowledgeBase';
import {
  api,
  IKbFile,
  IFaqFile,
  IStatusCount,
} from '@/services/api';

const { currentId } = storeToRefs(useKnowledgeBase());

type Status = 'green' | 'yellow' | 'red' | 'gray';

interface IDataSource {
  id: number;
  key: string;
  fileTag: string[];
  bytes: number | string;
  contentLength: number;
  fileId: string;
  fileIdName: string;
  status: Status;
  createtime: string;
  remark: { [key: string]: string } | string;
}

interface IFaqItem {
  id: number;
  faqId: string;
  question: string;
  answer: string;
  status: Status;
  bytes: string;
  createtime: string;
  picUrlList: Array<{ uid: number; name: string; status: string; url: string; originFileObj: File }>;
}

function kbFileToTable(file: IKbFile, index: number): IDataSource {
  return {
    key: file.id,
    id: 10000 + index,
    fileId: file.id,
    fileIdName: file.name,
    fileTag: file.tags,
    status: file.status as Status,
    bytes: formatFileSize(file.bytes || 0),
    contentLength: file.contentLength,
    createtime: file.createTime,
    remark: file.remark as IDataSource['remark'],
  };
}

function faqFileToTable(faq: IFaqFile, index: number): IFaqItem {
  return {
    id: 10000 + index,
    faqId: faq.id,
    question: faq.question,
    answer: faq.answer,
    status: faq.status as Status,
    bytes: `${faq.contentLength}字符`,
    createtime: faq.createTime,
    picUrlList: [],
  };
}

function updateStatusCount(target: IStatusCount, source: IStatusCount): void {
  Object.keys(target).forEach(key => {
    (target as Record<string, number>)[key] = 0;
  });
  Object.assign(target, source);
}

function hasParsingStatus(statusCount: IStatusCount): boolean {
  return statusCount.gray > 0 || statusCount.yellow > 0;
}

export const useOptiionList = defineStore(
  'option-list',
  () => {
    const dataSource = ref<IDataSource[]>([]);
    const setDataSource = (array: []) => {
      dataSource.value = array;
    };

    const totalStatus = ref<IStatusCount>({
      green: 0,
      gray: 0,
      yellow: 0,
      red: 0,
    });

    const kbTotal = ref(0);
    const setKbTotal = value => {
      kbTotal.value = value;
    };

    const kbPageNum = ref(1);
    const setKbPageNum = value => {
      kbPageNum.value = value;
    };

    const kbPageSize = ref(10);

    const faqList = ref<IFaqItem[]>([]);
    const setFaqList = (array: IFaqItem[]) => {
      faqList.value = array;
    };

    const total = ref(0);
    const setTotal = value => {
      total.value = value;
    };

    const pageNum = ref(1);
    const setPageNum = value => {
      pageNum.value = value;
    };

    const pageSize = ref(10);

    const loading = ref(false);
    const setLoading = value => {
      loading.value = value;
    };

    const faqType = ref('upload');
    const setFaqType = type => {
      faqType.value = type;
    };

    const editQaSet: any = ref(null);
    const setEditQaSet = value => {
      editQaSet.value = value;
    };

    const editModalVisible = ref(false);
    const setEditModalVisible = value => {
      editModalVisible.value = value;
    };

    const timer = ref<number | null>(null);

    const getDetails = async () => {
      if (timer.value) {
        clearTimeout(timer.value);
      }

      try {
        const result = await api.knowledge.getFileList({
          kb_id: currentId.value,
          page_id: kbPageNum.value,
          page_limit: kbPageSize.value,
        });

        updateStatusCount(totalStatus.value, result.statusCount);
        setDataSource([]);
        setKbTotal(result.total);

        result.files.forEach((file, index) => {
          dataSource.value.push(kbFileToTable(file, index));
        });

        if (hasParsingStatus(result.statusCount)) {
          timer.value = window.setTimeout(() => {
            if (timer.value) clearTimeout(timer.value);
            getDetails();
          }, 5000);
        } else {
          getProgressDetails();
        }
      } catch (e) {
        message.error((e as { msg?: string }).msg || '获取文件列表失败');
      }
    };

    const getProgressDetails = () => {
      let progressTimer: number | null = null;
      progressTimer = window.setInterval(async () => {
        try {
          const result = await api.knowledge.getFileList({
            kb_id: currentId.value,
            page_id: 1,
            page_limit: kbPageSize.value,
          });

          updateStatusCount(totalStatus.value, result.statusCount);
          setKbTotal(result.total);

          if (!hasParsingStatus(result.statusCount) && progressTimer !== null) {
            clearInterval(progressTimer);
            progressTimer = null;
          }
        } catch (e) {
          console.error(e);
        }
      }, 5000);
    };

    const faqTimer = ref<number | null>(null);

    const fetchImagesAsFiles = async (urls: string[]): Promise<File[]> => {
      const promises = urls.map(url =>
        fetch(url)
          .then(response => response.blob())
          .then(blob => {
            const filename = url.substring(url.lastIndexOf('/') + 1);
            return new File([blob], filename, { type: blob.type });
          })
      );
      return Promise.all(promises);
    };

    const enrichFaqImages = async (faqListArr: IFaqItem[], rawFaqs: IFaqFile[]) => {
      for (let i = 0; i < rawFaqs.length; i++) {
        const picUrls = rawFaqs[i].picUrlList;
        if (picUrls && picUrls.length > 0) {
          try {
            const files = await fetchImagesAsFiles(picUrls);
            faqListArr[i].picUrlList = picUrls.map((img, index) => ({
              uid: -index,
              name: 'image',
              status: 'done',
              url: img,
              originFileObj: files[index],
            }));
          } catch (errors) {
            console.error('获取图片文件出错:', errors);
          }
        }
      }
    };

    const getFaqList = async () => {
      try {
        if (faqTimer.value) {
          clearTimeout(faqTimer.value);
        }
        setLoading(true);

        const result = await api.knowledge.getFaqList({
          kb_id: currentId.value + '_FAQ',
          page_id: pageNum.value,
          page_limit: pageSize.value,
        });

        setFaqList([]);
        if (result.faqs.length === 0) {
          setTotal(0);
          setLoading(false);
          return;
        }

        setTotal(result.total);
        const tableItems: IFaqItem[] = result.faqs.map((faq, i) => faqFileToTable(faq, i));
        setFaqList(tableItems);
        enrichFaqImages(tableItems, result.faqs);

        if (hasParsingStatus(result.statusCount)) {
          faqTimer.value = window.setTimeout(() => {
            if (faqTimer.value) clearTimeout(faqTimer.value);
            getFaqList();
          }, 5000);
        }
      } catch (error) {
        console.log(error);
        message.error((error as { msg?: string }).msg || '获取faq列表失败');
      } finally {
        setLoading(false);
      }
    };

    return {
      dataSource,
      setDataSource,
      faqList,
      setFaqList,
      getDetails,
      timer,
      editQaSet,
      setEditQaSet,
      editModalVisible,
      setEditModalVisible,
      faqTimer,
      getFaqList,
      faqType,
      setFaqType,
      total,
      pageSize,
      setTotal,
      pageNum,
      setPageNum,
      loading,
      setLoading,
      totalStatus,
      kbTotal,
      kbPageSize,
      kbPageNum,
      setKbPageNum,
    };
  },
  {
    persist: {
      storage: sessionStorage,
    },
  }
);
