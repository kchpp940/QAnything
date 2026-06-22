<!--
 * @Author: 祝占朋 wb.zhuzhanpeng01@mesg.corp.netease.com
 * @Date: 2023-12-26 11:43:52
 * @LastEditors: 祝占朋 wb.zhuzhanpeng01@mesg.corp.netease.com
 * @LastEditTime: 2024-01-02 11:09:45
 * @FilePath: /qanything-open-source/src/components/AddInput.vue
 * @Description: 
-->
<template>
  <a-config-provider :theme="{ token: { colorPrimary: '#5a47e5' } }">
    <a-input v-model:value="kb_name" class="add-input" :placeholder="common.newPlaceholder">
      <template #prefix>
        <a-select v-model:value="addType" size="small">
          <a-select-option value="0">文档集</a-select-option>
          <a-select-option value="1">问答集</a-select-option>
        </a-select>
      </template>
      <template #suffix>
        <div class="add-button" @click="addKb">{{ common.new }}</div>
        <!--        <PlusCircleOutlined />-->
        <!--        <a-button shape="circle" size="small" :icon="h(CheckOutlined)" />-->
      </template>
    </a-input>
  </a-config-provider>
</template>
<script lang="ts" setup>
import { message } from 'ant-design-vue';
import { useKnowledgeBase } from '@/store/useKnowledgeBase';
import { getLanguage } from '@/language/index';
import { useOptiionList } from '@/store/useOptiionList';
import { useKnowledgeModal } from '@/store/useKnowledgeModal';
import { pageStatus } from '@/utils/enum';
import { api } from '@/services/api';

const { getList, setCurrentId, setCurrentKbName, setDefault } = useKnowledgeBase();
const { selectList } = storeToRefs(useKnowledgeBase());

const { setModalVisible } = useKnowledgeModal();
const { modalVisible } = storeToRefs(useKnowledgeModal());
const { setEditModalVisible } = useOptiionList();
const { editModalVisible } = storeToRefs(useOptiionList());

const common = getLanguage().common;
const kb_name = ref('');

// const emits = defineEmits(['add']);

const createKb = async (isFaq = false) => {
  return await api.knowledge.createKb({ kb_name: kb_name.value, is_faq: isFaq });
};

// 0是文档集，1是问答集
const addType = ref('0');

const addKb = async () => {
  if (!kb_name.value.length) {
    message.error(common.errorKnowledge);
    return;
  }

  try {
    const res = await createKb(addType.value !== '0');
    kb_name.value = '';
    setCurrentId(res?.id);
    setCurrentKbName(res?.name);
    selectList.value.push(res?.id);
    await getList();
    addType.value === '0'
      ? setModalVisible(!modalVisible.value)
      : setEditModalVisible(!editModalVisible.value);
    setDefault(pageStatus.optionlist);
  } catch (e) {
    console.log(e);
    message.error(e.msg || common.error);
  }
};
</script>

<style lang="scss" scoped>
.add-button {
  cursor: pointer;
  width: 48px;
  height: 24px;
  border-radius: 4px;
  background: #5a47e5;
  font-size: 14px;
  //font-weight: 500;
  line-height: 24px;
  text-align: center;
  color: #fff;
}
</style>
