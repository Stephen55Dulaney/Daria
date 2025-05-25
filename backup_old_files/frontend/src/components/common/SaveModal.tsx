import React, { useState } from 'react';
import { Modal, Input, Button, Form, message } from 'antd';

interface SaveModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (name: string, description: string) => Promise<void>;
  title: string;
  type: 'persona' | 'journey-map';
  loading?: boolean;
}

const SaveModal: React.FC<SaveModalProps> = ({ 
  isOpen, 
  onClose, 
  onSave, 
  title, 
  type,
  loading = false 
}) => {
  const [form] = Form.useForm();
  
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await onSave(values.name, values.description);
      form.resetFields();
    } catch (error) {
      console.error('Error saving:', error);
      message.error('Failed to save. Please try again.');
    }
  };

  return (
    <Modal
      title={title}
      open={isOpen}
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>Cancel</Button>,
        <Button 
          key="save" 
          type="primary" 
          onClick={handleSubmit} 
          loading={loading}
        >
          Save
        </Button>
      ]}
    >
      <Form form={form} layout="vertical">
        <Form.Item 
          name="name" 
          label="Name"
          rules={[{ required: true, message: 'Please enter a name' }]}
        >
          <Input placeholder={`Enter ${type} name`} />
        </Form.Item>
        <Form.Item 
          name="description" 
          label="Description"
        >
          <Input.TextArea 
            placeholder={`Enter a brief description of this ${type}`}
            rows={4}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default SaveModal; 