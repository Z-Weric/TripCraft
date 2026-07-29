import { useState } from "react";
import { Form, Input, InputNumber, Select, Button, Checkbox, message } from "antd";
import { EnvironmentOutlined, CalendarOutlined, DollarOutlined, HeartOutlined } from "@ant-design/icons";
import type { GenerateRequest } from "../services/api";

const { Option } = Select;

const PREFERENCES = ["美食", "自然风光", "亲子", "购物", "历史文化"];

interface SearchBarProps {
  onGenerate: (req: GenerateRequest) => void;
  loading: boolean;
}

export default function SearchBar({ onGenerate, loading }: SearchBarProps) {
  const [form] = Form.useForm();
  const [destination, setDestination] = useState("杭州");
  const [days, setDays] = useState(3);
  const [budget, setBudget] = useState(2000);
  const [preferences, setPreferences] = useState<string[]>(["美食", "自然风光", "亲子"]);

  const handleSubmit = () => {
    if (!destination.trim()) {
      message.warning("请输入目的地");
      return;
    }
    onGenerate({
      destination: destination.trim(),
      days,
      budget,
      preferences,
    });
  };

  const formItemStyle = { marginBottom: 16 };

  return (
    <div
      style={{
        background: "#FFFFFF",
        border: "2px solid #C9622A",
        borderRadius: 2,
        padding: "20px 24px",
      }}
    >
      <div
        style={{
          fontSize: 15,
          fontWeight: 600,
          color: "#6B5B4A",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          marginBottom: 16,
        }}
      >
        规划你的旅程
      </div>

      <Form form={form} layout="vertical">
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <Form.Item label="目的地" style={{ ...formItemStyle, flex: "1 1 150px" }}>
            <Input
              prefix={<EnvironmentOutlined style={{ color: "#8B7B6A" }} />}
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="输入城市名"
              style={{ borderBottom: "1px solid #E8DCC8" }}
            />
          </Form.Item>

          <Form.Item label="天数" style={{ ...formItemStyle, flex: "1 1 100px" }}>
            <Select
              value={days}
              onChange={setDays}
              suffixIcon={<CalendarOutlined style={{ color: "#8B7B6A" }} />}
            >
              <Option value={2}>2 天</Option>
              <Option value={3}>3 天</Option>
              <Option value={5}>5 天</Option>
            </Select>
          </Form.Item>

          <Form.Item label="预算 (元)" style={{ ...formItemStyle, flex: "1 1 120px" }}>
            <InputNumber
              prefix={<DollarOutlined style={{ color: "#8B7B6A" }} />}
              value={budget}
              onChange={(v) => setBudget(v || 2000)}
              min={500}
              max={50000}
              step={500}
              style={{ width: "100%" }}
            />
          </Form.Item>

          <Form.Item label=" " style={{ ...formItemStyle, flex: "0 0 auto" }}>
            <Button
              type="primary"
              onClick={handleSubmit}
              loading={loading}
              style={{
                background: "#C9622A",
                borderColor: "#C9622A",
                borderRadius: 2,
                fontWeight: 600,
                letterSpacing: "0.04em",
                height: 32,
              }}
            >
              生成攻略
            </Button>
          </Form.Item>
        </div>

        <Form.Item label="偏好" style={{ marginBottom: 0 }}>
          <Checkbox.Group
            value={preferences}
            onChange={(vals) => setPreferences(vals as string[])}
          >
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {PREFERENCES.map((pref) => (
                <Checkbox
                  key={pref}
                  value={pref}
                  style={{
                    margin: 0,
                    padding: "5px 16px",
                    border: "1px solid #D4C4A8",
                    borderRadius: 20,
                    fontSize: 13,
                    color: "#6B5B4A",
                  }}
                >
                  {pref}
                </Checkbox>
              ))}
            </div>
          </Checkbox.Group>
        </Form.Item>
      </Form>
    </div>
  );
}