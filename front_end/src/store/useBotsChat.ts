/*
 * @Author: 祝占朋 wb.zhuzhanpeng01@mesg.corp.netease.com
 * @Date: 2023-12-27 19:21:14
 * @LastEditors: 祝占朋 wb.zhuzhanpeng01@mesg.corp.netease.com
 * @LastEditTime: 2023-12-29 11:05:53
 * @FilePath: /ai-demo/src/store/useChat.ts
 * @Description:
 */
import { IChatItem } from '@/utils/types';

export const useBotsChat = defineStore({
  id: 'useBotsChat',
  state: () => ({
    QA_List: [] as Array<IChatItem>,
    showModal: false,
  }),
  actions: {
    clearQAList() {
      this.QA_List = [];
    },
    setQaList(newQaList: Array<IChatItem>) {
      this.QA_List = newQaList;
    },
  },
  {
    persist: {
      storage: localStorage,
    },
  }
);
