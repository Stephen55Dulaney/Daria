import React, { useState } from 'react';
import { Form, Input, Button, Select, message, Radio } from 'antd';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const { Option } = Select;

const experienceLevels = ['Junior', 'Mid-Level', 'Senior', 'Lead'];
const interviewTypes = [
  'Application Interview',
  'Persona Interview',
  'Journey Map Interview',
];
const emotions = ['Satisfied', 'Frustrated', 'Confused', 'Neutral', 'Angry', 'Happy'];
const statuses = ['Draft', 'In Progress', 'Completed', 'Validated'];

const CreateInterview: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values: any) => {
    setLoading(true);
    // Convert tags to array
    const tags = values.tags
      ? values.tags.split(',').map((tag: string) => tag.trim()).filter((tag: string) => tag)
      : [];
    try {
      const response = await axios.post('/save_interview', {
        project_name: values.projectName,
        interview_type: values.interviewType,
        project_description: values.projectDescription,
        participant_name: values.participantName,
        role: values.participantRole,
        experience_level: values.experienceLevel,
        department: values.department,
        tags,
        emotion: values.emotion,
        status: values.status,
        author: values.author,
      });
      if (response.data && response.data.redirect_url) {
        message.success('Interview configuration saved! Redirecting...');
        setTimeout(() => navigate(response.data.redirect_url), 1000);
      } else {
        message.error('Unexpected response from server.');
      }
    } catch (error: any) {
      message.error(error.response?.data?.error || 'Failed to save interview.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Create New Interview</h1>
      <Form form={form} layout="vertical" onFinish={onFinish}>
        {/* Project Info */}
        <Form.Item label="Project Name" name="projectName" rules={[{ required: true }]}> <Input /> </Form.Item>
        <Form.Item label="Interview Type" name="interviewType" rules={[{ required: true }]}> <Select placeholder="Select interview type"> {interviewTypes.map(type => <Option key={type} value={type}>{type}</Option>)} </Select> </Form.Item>
        <Form.Item label="Project Description" name="projectDescription" rules={[{ required: true }]}> <Input.TextArea rows={3} /> </Form.Item>
        {/* Participant Info */}
        <Form.Item label="Participant Name" name="participantName"> <Input /> </Form.Item>
        <Form.Item label="Role" name="participantRole"> <Input /> </Form.Item>
        <Form.Item label="Experience Level" name="experienceLevel"> <Select allowClear placeholder="Select experience level"> {experienceLevels.map(level => <Option key={level} value={level}>{level}</Option>)} </Select> </Form.Item>
        <Form.Item label="Department" name="department"> <Input /> </Form.Item>
        {/* Interview Metadata */}
        <Form.Item label="Tags" name="tags"> <Input placeholder="Enter tags separated by commas" /> </Form.Item>
        <Form.Item label="Primary Emotion" name="emotion"> <Select allowClear placeholder="Select primary emotion"> {emotions.map(e => <Option key={e} value={e}>{e}</Option>)} </Select> </Form.Item>
        <Form.Item label="Interview Status" name="status" initialValue="Draft"> <Select> {statuses.map(s => <Option key={s} value={s}>{s}</Option>)} </Select> </Form.Item>
        <Form.Item label="Interviewer Name" name="author"> <Input placeholder="Your name" /> </Form.Item>
        <Form.Item> <Button type="primary" htmlType="submit" loading={loading}> Start Interview </Button> </Form.Item>
      </Form>
    </div>
  );
};

export default CreateInterview; 