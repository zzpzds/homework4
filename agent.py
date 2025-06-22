import asyncio
from typing import List, Literal
from dataclasses import dataclass, field
from openai import AsyncOpenAI
from agents import Agent, Runner, function_tool, OpenAIProvider
import json
import random
import time

# 初始化OpenAI客户端
client = AsyncOpenAI(api_key="sk-zO8exlBicZh7nJeZn5GuC5X9SPuVrZzXoGyOW0i9BFvN62ON")

# 1. DSL 数据模型定义
@dataclass
class FlowStep:
    step: str
    entity: Literal["User", "System"]
    action: str

@dataclass
class AlternativeFlow:
    condition: str
    steps: List[FlowStep]

@dataclass
class UserStory:
    title: str
    actor: str
    basic_flow: List[FlowStep]
    alternative_flows: List[AlternativeFlow]

@dataclass
class UseCaseDiagram:
    actors: List[str]
    use_cases: List[str]
    relationships: List[dict]

@dataclass
class SequenceDiagram:
    title: str
    participants: List[str]
    steps: List[dict]

@dataclass
class ClassAttribute:
    name: str
    type: str

@dataclass
class ClassMethod:
    name: str
    parameters: List[str] = field(default_factory=list)

@dataclass
class ClassDefinition:
    name: str
    attributes: List[ClassAttribute]
    methods: List[ClassMethod]

@dataclass
class OCLContract:
    context: str
    preconditions: List[str]
    postconditions: List[str]

@dataclass
class RequirementModel:
    user_stories: List[UserStory]
    use_case_diagram: UseCaseDiagram
    sequence_diagrams: List[SequenceDiagram]
    class_diagram: List[ClassDefinition]
    ocl_contracts: List[OCLContract]

# 2. 工具函数定义

@function_tool
def ai_design_to_code(design_image_id: str, preferences: dict) -> dict:
    """
    调用AI设计图转样式代码服务，节省开发人力
    参数:
        design_image_id: 设计图的唯一标识
        preferences: 开发者的代码偏好设置
    返回:
        {
            "status": "success" | "error",
            "code": "生成的代码字符串",
            "confidence_score": 0.0-1.0,
            "warnings": [""]
        }
    """
    print(f"调用AI D2C服务: 转换设计图 {design_image_id}，偏好设置: {preferences}")
    
    # 模拟处理时间
    time.sleep(1)
    
    # 随机生成置信度分数
    confidence = round(random.uniform(0.85, 0.98), 2)
    
    # 20%概率模拟低置信度情况
    if random.random() < 0.2:
        confidence = round(random.uniform(0.7, 0.89), 2)
        return {
            "status": "warning",
            "code": f"/* AI生成的代码 (置信度: {confidence}) */",
            "confidence_score": confidence,
            "warnings": ["AI置信度低于90%，可能需要手动调整"]
        }
    
    return {
        "status": "success",
        "code": f"/* 高质量AI生成代码 (置信度: {confidence}) */",
        "confidence_score": confidence,
        "warnings": []
    }

@function_tool
def send_notification(user_id: str, message: str, notification_type: str = "info") -> bool:
    """
    向指定用户发送通知，告知设计图接收和开发进度
    参数:
        user_id: 用户ID
        message: 通知内容
        notification_type: 通知类型 (info/success/warning/error)
    返回:
        发送是否成功
    """
    print(f"发送通知给用户 {user_id}: [{notification_type}] {message}")
    # 在实际系统中，这里会调用消息服务API
    return True

# 3. Agent 定义Prompt

# Agent 1: 需求解析器
requirement_parser = Agent(
    name="RequirementParser",
    model="gpt-4o",
    instructions="""
    你是一个需求分析专家，负责将自然语言需求转化为结构化DSL。请按以下规则处理：
    1. 识别所有用户故事（As a... I want to...）
    2. 提取每个用户故事的：
       - 参与者（Actor）
       - 基本流（Basic Flow）
       - 备选流（Alternative Flow）
    3. 使用以下JSON格式输出：
    {
      "user_stories": [{
        "title": "As a...",
        "actor": "",
        "basic_flow": [{"step": 1, "entity": "User/System", "action": ""}],
        "alternative_flows": [{
          "condition": "", 
          "steps": [{"step": "A1", "entity": "", "action": ""}]
        }]
      }]
    }
    4. 严格保持原始需求的语义完整性
    """,
    tools=[],
    output_type=List[UserStory]
)

# Agent 2: 用例建模
use_case_modeler = Agent(
    name="UseCaseModeler",
    model="gpt-4o",
    instructions="""
    你是用例建模专家，基于结构化需求生成：
    1. 用例图（包含Actor、UseCase及其关系）
    2. 系统顺序图（包含消息序列）
    使用以下JSON格式：
    {
      "use_case_diagram": {
        "actors": ["Designer", "Developer"],
        "use_cases": ["Upload Design", "Review Designs", ...],
        "relationships": [
          {"actor": "Designer", "use_case": "Upload Design"},
          {"actor": "Developer", "use_case": "Convert Design to Code"}
        ]
      },
      "sequence_diagrams": [{
        "title": "Upload Design",
        "participants": ["Designer", "Platform"],
        "steps": [
          {"seq": 1, "from": "Designer", "to": "Platform", "message": "opens file dialog"},
          {"seq": 2, "from": "Platform", "to": "Platform", "message": "validates format"}
        ],
        "alt_flows": [
          {"condition": "Invalid format", "steps": [...]}
        ]
      }]
    }
    """,
    tools=[send_notification],
    output_type=dict
)

# Agent 3: 类图建模
class_modeler = Agent(
    name="ClassModeler",
    model="gpt-4o",
    instructions="""
    你是类建模专家，生成：
    1. 概念类图（类、属性、关联关系）
    2. OCL合约（前置/后置条件）
    使用JSON格式：
    {
      "class_diagram": [
        {
          "name": "DesignImage",
          "attributes": [
            {"name": "id", "type": "UUID"},
            {"name": "format", "type": "string"}
          ],
          "methods": [
            {"name": "validate_format", "parameters": []}
          ]
        }
      ],
      "ocl_contracts": [
        {
          "context": "DesignImage::upload()",
          "preconditions": ["self.size <= MAX_SIZE"],
          "postconditions": ["Platform.designs.includes(self)"]
        }
      ]
    }
    """,
    tools=[send_notification],
    output_type=dict
)

# Agent 4: 工作流协调
workflow_orchestrator = Agent(
    name="WorkflowOrchestrator",
    model="gpt-4o",
    instructions="""
    你是工作流协调员，负责：
    1. 整合RequirementParser/UseCaseModeler/ClassModeler的输出
    2. 生成最终需求模型
    3. 使用以下整合格式：
    {
      "requirements_model": {
        "user_stories": [...],  // From RequirementParser
        "use_case_model": { ... },  // From UseCaseModeler
        "class_model": { ... },     // From ClassModeler
        "timestamp": "2025-06-23T10:30:00Z"
      }
    }
    4. 验证模型一致性，解决冲突
    """,
    tools=[ai_design_to_code, send_notification],
    output_type=RequirementModel
)

# 4. 多Agent工作流执行
async def run_workflow(requirements: str) -> RequirementModel:
    # 创建OpenAI提供者
    provider = OpenAIProvider(
        openai_client=client,
        use_responses=False,
    )
    
    # 步骤1: 需求解析
    print("Running RequirementParser...")
    parser_result = await Runner.run(
        requirement_parser,
        input=requirements,
        model_provider=provider
    )
    user_stories = parser_result.final_output
    
    # 将输出转换为JSON字符串供后续Agent使用
    parser_output_str = json.dumps([us.__dict__ for us in user_stories])
    
    # 步骤2: 并行执行用例建模和类图建模
    print("Running UseCaseModeler and ClassModeler...")
    use_case_task = Runner.run(
        use_case_modeler,
        input=parser_output_str,
        model_provider=provider
    )
    
    class_model_task = Runner.run(
        class_modeler,
        input=parser_output_str,
        model_provider=provider
    )
    
    use_case_result, class_model_result = await asyncio.gather(
        use_case_task, class_model_task
    )
    
    # 步骤3: 整合最终模型
    print("Running WorkflowOrchestrator...")
    # 准备输入数据
    input_data = json.dumps({
        "user_stories": [us.__dict__ for us in user_stories],
        "use_case_model": use_case_result.final_output,
        "class_model": class_model_result.final_output
    })
    
    orchestrator_result = await Runner.run(
        workflow_orchestrator,
        input=input_data,
        model_provider=provider
    )
    
    return orchestrator_result.final_output

# 主执行函数
if __name__ == "__main__":
    # 示例需求模型的自然语言定义
    requirements = """
    As a designer, I want to select and upload design drafts to platform, so that all design images are centralized
    {
        Basic Flow {
            (User)1. the designer shall opens a file dialog and selects design image.
            (System)2. the platform shall validates file format.
            (System)3. the platform shall uploads image to database and generates thumbnail previews and stores metadata.
        }
        Alternative Flow {
            A. At any time, Invalid file format detected :
                1. Displays an error message like Unsupported file format and Please upload PNG JPG SVG.
            B. At any time, Upload failure :
                1. Notify user like Upload failed and Please try again.
            C. At any time, File exceeds a size limit :
                1. Shows like File size exceeds limit and Maximum allowed xMB.
        }
    }
    As a developer, I want to review all design images and select a method to convert images to code
    {
        Basic Flow {
            (System)1. the platform shall displays a paginated list of design images with thumbnails and metadata and tags.
            (System)2. the platform shall enables filtering and searching by tags and upload date or designer ID.
            (User)3. the developer shall selects a design image.
            (System)4. the platform shall provides zoomable high resolution previews for detailed inspection.
        }
        Alternative Flow {
            A. At any time, No design images available :
                1. Shows a placeholder message like No designs found and Upload a design first.
        }
    }
    As a developer, I want to choose between AI generated code or manual development for selected design
    {
        Basic Flow {
            (User)1. the developer shall selects a design image.
            (System)2. the Prompts developer shall to choose a conversion method between AI Auto Convert and Manual Development.
            (System)3. the AI mode platform shall allows specifying code preferences.
            (User)4. the developer shall selects desired option.
            (System)5. the platform shall mark status of selected design image to doing.
        }
        Alternative Flow {
            A. At any time, AI service unavailable :
                1. notify AI service is temporarily unavailable and please try manual mode.
        }
    }
    As a developer, I want to platform to auto convert design into code via AI and provide downloadable results
    {
        Basic Flow {
            (User)1. the developer shall selects AI Auto Convert.
            (System)2. the platform shall calls an AI conversion service and generates clean and annotated code.
            (System)3. the platform shall validates code integrity and packages it into a ZIP file.
            (System)4. the platform shall triggers a download and logs activity.
            (User)5. the developer shall select a file position for download result ZIP file.
        }
        Alternative Flow {
            A. At any time, AI confidence score lower than ninty percent :
                1. Warns Conversion may require manual adjustments and Proceed.
            B. At any time, Code validation errors :
                2. Highlights errors and offers retry options.
        }
    }
    As a developer, I want to download design image for manual development
    {
        Basic Flow {
            (User)1. the developer shall selects Manual Development.
            (System)2. the platform shall provides original design image as a downloadable file.
            (System)3. the platform shall extracts design assets into a folder.
        }
        Alternative Flow {
            A. At any time, Image corruption detected :
                1. Notify Image file is corrupted and Please reupload design.
        }
    }
    As a designer, I want to know whether any developer had accepted my design image
    {
        Basic Flow {
            (System)1. the platform shall send a message to designer after any developer accepted design image.
            (User)2. the user shall receive palaform messages in person message center.
        }
    }
    """
    
    # 执行完整工作流
    print("Starting MultiAgent workflow...")
    result = asyncio.run(run_workflow(requirements))
    