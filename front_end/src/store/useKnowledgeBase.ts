/*
 * @Author: 祝占朋 wb.zhuzhanpeng01@mesg.corp.netease.com
 * @Date: 2024-01-09 15:28:56
 * @LastEditors: Ianarua 306781523@qq.com
 * @LastEditTime: 2024-08-02 16:02:06
 * @FilePath: front_end/src/store/useKnowledgeBase.ts
 * @Description:
 */

import { pageStatus } from '@/utils/enum';
import message from 'ant-design-vue/es/message';
import { getLanguage } from '@/language/index';
import { api, IKnowledgeBase } from '@/services/api';

const common = getLanguage().common;

export type { IKnowledgeBase } from '@/services/api';

export const useKnowledgeBase = defineStore(
  'knowledgeBase',
  () => {
    const currentId = ref('');
    const setCurrentId = (id: string) => {
      currentId.value = id;
    };

    watch(
      () => currentId.value,
      () => {
        console.log('current', currentId.value);
      }
    );

    const selectList = ref<string[]>([]);
    const setSelectList = list => {
      selectList.value = list;
    };

    const currentKbName = ref('');
    const setCurrentKbName = (id: string) => {
      currentKbName.value = id;
    };

    const knowledgeBaseList = ref<Array<IKnowledgeBase>>([]);
    const setKnowledgeBaseList = list => {
      knowledgeBaseList.value = list;
    };

    const showDefault = ref(pageStatus.initing);
    const setDefault = str => {
      showDefault.value = str;
    };

    const showDeleteModal = ref(false);
    const setShowDeleteModal = (flag: boolean) => {
      showDeleteModal.value = flag;
    };

    const getList = async () => {
      try {
        const list = await api.knowledge.getKbList();
        if (list.length > 0) {
          setKnowledgeBaseList(list);
          setDefault(pageStatus.normal);

          if (!selectList.value.length) {
            selectList.value.push(list[0]?.id);
          }
        } else {
          setKnowledgeBaseList([]);
          setDefault(pageStatus.default);
        }
      } catch (e) {
        setKnowledgeBaseList([]);
        setDefault(pageStatus.default);
        message.error((e as { msg?: string }).msg || common.error);
      }
    };

    return {
      currentId,
      setCurrentId,
      knowledgeBaseList,
      setKnowledgeBaseList,
      showDeleteModal,
      setShowDeleteModal,
      showDefault,
      setDefault,
      getList,
      currentKbName,
      setCurrentKbName,
      selectList,
      setSelectList,
    };
  },
  {
    persist: {
      storage: localStorage,
    },
  }
);
