import React, { useEffect } from 'react';
import { Form, Input, Button, Radio, Upload, Checkbox, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';

const UploadTranscript: React.FC = () => {
  const [form] = Form.useForm();

  useEffect(() => {
    // One-time sync for autofilled values
    const fields = [
      { key: 'name', selector: 'input' },
      { key: 'email', selector: 'input' },
      { key: 'role', selector: 'input' },
      { key: 'projectName', selector: 'input' },
      { key: 'transcriptName', selector: 'input' },
      { key: 'projectDescription', selector: 'textarea' },
    ];
    const values: any = {};
    fields.forEach(({ key, selector }) => {
      const el = document.querySelector(`${selector}[name=\"${key}\"]`) as HTMLInputElement | HTMLTextAreaElement | null;
      if (el && el.value) {
        values[key] = el.value;
      }
    });
    if (Object.keys(values).length > 0) {
      form.setFieldsValue(values);
    }
  }, [form]);

  const normFile = (e: any) => {
    if (Array.isArray(e)) {
      return e;
    }
    return e && e.fileList;
  };

  const onFinish = async (values: any) => {
    const formData = new FormData();
    Object.entries(values).forEach(([key, value]) => {
      if (key !== 'transcriptFile') {
        // Only append string values
        if (typeof value === 'string' || typeof value === 'boolean') {
          formData.append(key, String(value));
        }
      }
    });
    values.transcriptFile.forEach((file: any) => {
      formData.append('transcriptFile', file.originFileObj);
    });

    try {
      const response = await fetch('http://localhost:5003/upload_transcript', {
        method: 'POST',
        body: formData,
      });

      // Try to parse JSON only if response is ok and has content
      let data = null;
      const text = await response.text();
      if (text) {
        data = JSON.parse(text);
      }

      if (response.ok && data && data.transcript_id) {
        window.location.href = `/transcript/${data.transcript_id}`;
      } else {
        message.error('Upload failed: ' + (data?.error || response.statusText || 'Unknown error'));
      }
    } catch (error: any) {
      message.error('Upload failed: ' + (error.message || error));
    }
  };

  const onFinishFailed = (errorInfo: any) => {
    console.log('Form validation failed:', errorInfo);
    message.error('Please fill all required fields. See console for details.');
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Upload Transcript</h1>
      <Form
        form={form}
        layout="vertical"
        initialValues={{ consent: false }}
        onFinish={onFinish}
        onFinishFailed={onFinishFailed}
        autoComplete="off"
      >
        <Form.Item label="Name" name="name" rules={[{ required: true, message: "Name is required" }]}>
          <Input autoComplete="name" name="name" />
        </Form.Item>
        <Form.Item label="Email" name="email" rules={[{ required: true, type: 'email', message: "Valid email is required" }]}>
          <Input autoComplete="email" name="email" />
        </Form.Item>
        <Form.Item label="Role" name="role" rules={[{ required: true, message: "Role is required" }]}>
          <Input autoComplete="organization-title" name="role" />
        </Form.Item>
        <Form.Item label="Project Name" name="projectName" rules={[{ required: true, message: "Project Name is required" }]}>
          <Input autoComplete="off" name="projectName" />
        </Form.Item>
        <Form.Item
          label="Interview Type"
          name="interviewType"
          rules={[{ required: true, message: "Interview Type is required" }]}
        >
          <Radio.Group>
            <Radio value="Persona Interview">Persona Interview</Radio>
            <Radio value="Journey Map Interview">Journey Map Interview</Radio>
            <Radio value="Application Interview">Application Interview</Radio>
          </Radio.Group>
        </Form.Item>
        <Form.Item label="Project Description" name="projectDescription" rules={[{ required: true, message: "Project Description is required" }]}>
          <Input.TextArea autoComplete="off" name="projectDescription" />
        </Form.Item>
        <Form.Item label="Transcript Name" name="transcriptName" rules={[{ required: true, message: "Transcript Name is required" }]}>
          <Input autoComplete="off" name="transcriptName" />
        </Form.Item>
        <Form.Item
          label="Upload Transcript"
          name="transcriptFile"
          valuePropName="fileList"
          getValueFromEvent={normFile}
          rules={[{ required: true, message: 'Please upload a transcript file.' }]}
        >
          <Upload beforeUpload={() => false} maxCount={1} accept=".txt,.doc,.docx,.pdf">
            <Button icon={<UploadOutlined />}>Select File</Button>
          </Upload>
        </Form.Item>
        <Form.Item
          name="consent"
          valuePropName="checked"
          rules={[{ required: true, message: 'Consent is required' }]}
        >
          <Checkbox>
            I confirm I have consent to upload this transcript and all information is accurate.
          </Checkbox>
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit">Submit</Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export default UploadTranscript; 