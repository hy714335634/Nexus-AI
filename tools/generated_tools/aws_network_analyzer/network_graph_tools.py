from strands import tool
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import io
import base64
import json
from typing import Dict, Any, Optional, List, Union, Tuple
import tempfile
import os
from datetime import datetime

@tool
def networkx(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    layout_type: str = "spring",
    node_size_field: Optional[str] = None,
    node_color_field: Optional[str] = None,
    edge_width_field: Optional[str] = None,
    node_label_field: Optional[str] = None,
    edge_label_field: Optional[str] = None,
    title: Optional[str] = None,
    figsize: Tuple[int, int] = (12, 10),
    output_format: str = "png",
    dpi: int = 300,
    directed: bool = False,
    save_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    使用NetworkX创建网络拓扑图。
    
    Args:
        nodes: 节点列表，每个节点是一个包含id和其他属性的字典
        edges: 边列表，每个边是一个包含source、target和其他属性的字典
        layout_type: 布局类型，可选值：spring, circular, shell, spectral, kamada_kawai, random
        node_size_field: 用于确定节点大小的节点属性字段名
        node_color_field: 用于确定节点颜色的节点属性字段名
        edge_width_field: 用于确定边宽度的边属性字段名
        node_label_field: 用于显示节点标签的节点属性字段名
        edge_label_field: 用于显示边标签的边属性字段名
        title: 图表标题
        figsize: 图形大小，格式为(宽, 高)
        output_format: 输出格式，可选值：png, svg, pdf
        dpi: 图像DPI（每英寸点数）
        directed: 是否为有向图
        save_path: 保存图像的路径，如果不提供则返回Base64编码的图像数据
    
    Returns:
        Dict[str, Any]: 包含图像数据或文件路径的字典
    """
    try:
        # 创建图
        G = nx.DiGraph() if directed else nx.Graph()
        
        # 添加节点
        for node in nodes:
            node_id = node.get('id')
            if node_id is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "节点必须包含id字段"
                }
            
            # 添加节点及其属性
            G.add_node(node_id, **{k: v for k, v in node.items() if k != 'id'})
        
        # 添加边
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            if source is None or target is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "边必须包含source和target字段"
                }
            
            # 添加边及其属性
            G.add_edge(source, target, **{k: v for k, v in edge.items() if k not in ['source', 'target']})
        
        # 选择布局
        pos = None
        if layout_type == 'spring':
            pos = nx.spring_layout(G)
        elif layout_type == 'circular':
            pos = nx.circular_layout(G)
        elif layout_type == 'shell':
            pos = nx.shell_layout(G)
        elif layout_type == 'spectral':
            pos = nx.spectral_layout(G)
        elif layout_type == 'kamada_kawai':
            pos = nx.kamada_kawai_layout(G)
        elif layout_type == 'random':
            pos = nx.random_layout(G)
        else:
            pos = nx.spring_layout(G)  # 默认使用spring布局
        
        # 创建图形
        fig = Figure(figsize=figsize)
        ax = fig.add_subplot(111)
        
        # 设置标题
        if title:
            ax.set_title(title)
        
        # 准备节点大小
        node_size = 300  # 默认大小
        if node_size_field and all(node_size_field in node for node in nodes):
            # 从节点属性获取大小值
            size_values = [G.nodes[node.get('id')].get(node_size_field, 300) for node in nodes]
            # 归一化大小值到合理范围
            if size_values:
                min_size, max_size = 100, 1000
                min_val, max_val = min(size_values), max(size_values)
                if min_val != max_val:
                    node_size = [min_size + (val - min_val) * (max_size - min_size) / (max_val - min_val) for val in size_values]
                else:
                    node_size = 500
        
        # 准备节点颜色
        node_color = 'skyblue'  # 默认颜色
        if node_color_field and all(node_color_field in node for node in nodes):
            node_color = [G.nodes[node.get('id')].get(node_color_field, 'skyblue') for node in nodes]
        
        # 准备边宽度
        edge_width = 1.0  # 默认宽度
        if edge_width_field and all(edge_width_field in edge for edge in edges):
            # 从边属性获取宽度值
            width_values = [G.edges[edge.get('source'), edge.get('target')].get(edge_width_field, 1.0) for edge in edges]
            # 归一化宽度值到合理范围
            if width_values:
                min_width, max_width = 1.0, 5.0
                min_val, max_val = min(width_values), max(width_values)
                if min_val != max_val:
                    edge_width = [min_width + (val - min_val) * (max_width - min_width) / (max_val - min_val) for val in width_values]
                else:
                    edge_width = 2.0
        
        # 准备节点标签
        node_labels = None
        if node_label_field:
            node_labels = {node.get('id'): G.nodes[node.get('id')].get(node_label_field, str(node.get('id'))) for node in nodes}
        
        # 绘制网络
        nx.draw_networkx(
            G, 
            pos=pos,
            with_labels=node_labels is not None,
            labels=node_labels,
            node_size=node_size,
            node_color=node_color,
            width=edge_width,
            arrows=directed,
            ax=ax
        )
        
        # 添加边标签
        if edge_label_field:
            edge_labels = {(edge.get('source'), edge.get('target')): G.edges[edge.get('source'), edge.get('target')].get(edge_label_field, '') for edge in edges}
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)
        
        # 保存或返回图像
        if save_path:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            fig.savefig(save_path, format=output_format, dpi=dpi, bbox_inches='tight')
            return {
                "status": "success",
                "file_path": save_path,
                "message": f"网络图已保存到 {save_path}"
            }
        else:
            # 返回Base64编码的图像
            buf = io.BytesIO()
            fig.savefig(buf, format=output_format, dpi=dpi, bbox_inches='tight')
            buf.seek(0)
            img_data = base64.b64encode(buf.read()).decode('utf-8')
            return {
                "status": "success",
                "image_data": img_data,
                "image_format": output_format,
                "image_size": len(img_data)
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }

@tool
def graphviz(
    dot_string: str,
    output_format: str = "png",
    save_path: Optional[str] = None,
    title: Optional[str] = None,
    dpi: int = 300
) -> Dict[str, Any]:
    """
    使用Graphviz创建网络拓扑图。
    
    Args:
        dot_string: Graphviz DOT格式字符串
        output_format: 输出格式，可选值：png, svg, pdf
        save_path: 保存图像的路径，如果不提供则返回Base64编码的图像数据
        title: 图表标题（如果DOT字符串中未指定）
        dpi: 图像DPI（每英寸点数）
    
    Returns:
        Dict[str, Any]: 包含图像数据或文件路径的字典
    """
    try:
        import graphviz as gv
        
        # 如果提供了标题且DOT字符串中没有标题，添加标题
        if title and 'label=' not in dot_string:
            # 检查DOT字符串是否以图定义开头
            if dot_string.strip().startswith('digraph') or dot_string.strip().startswith('graph'):
                # 在第一个花括号后添加标题
                open_brace_index = dot_string.find('{')
                if open_brace_index != -1:
                    dot_string = dot_string[:open_brace_index+1] + f' label="{title}"; ' + dot_string[open_brace_index+1:]
        
        # 创建Graphviz对象
        src = gv.Source(dot_string)
        
        # 保存或返回图像
        if save_path:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            
            # 渲染并保存
            src.render(filename=os.path.splitext(save_path)[0], format=output_format, cleanup=True)
            
            return {
                "status": "success",
                "file_path": f"{os.path.splitext(save_path)[0]}.{output_format}",
                "message": f"网络图已保存到 {os.path.splitext(save_path)[0]}.{output_format}"
            }
        else:
            # 渲染到内存
            with tempfile.NamedTemporaryFile(suffix=f'.{output_format}') as tmp:
                tmp_path = os.path.splitext(tmp.name)[0]
                src.render(filename=tmp_path, format=output_format, cleanup=True)
                
                # 读取生成的文件
                rendered_file = f"{tmp_path}.{output_format}"
                with open(rendered_file, 'rb') as f:
                    img_data = base64.b64encode(f.read()).decode('utf-8')
                
                # 清理临时文件
                try:
                    os.remove(rendered_file)
                except:
                    pass
                
                return {
                    "status": "success",
                    "image_data": img_data,
                    "image_format": output_format,
                    "image_size": len(img_data)
                }
    
    except ImportError:
        return {
            "status": "error",
            "error_type": "ImportError",
            "error_message": "Graphviz包未安装。请使用'pip install graphviz'安装Python包，并确保系统中安装了Graphviz。"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }

@tool
def matplotlib(
    data: Dict[str, Any],
    chart_type: str,
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 6),
    output_format: str = "png",
    dpi: int = 300,
    save_path: Optional[str] = None,
    color_map: Optional[str] = "viridis",
    grid: bool = True,
    legend: bool = True
) -> Dict[str, Any]:
    """
    使用Matplotlib创建各种图表。
    
    Args:
        data: 图表数据，格式取决于chart_type
        chart_type: 图表类型，可选值：bar, line, scatter, pie, heatmap, histogram
        title: 图表标题
        xlabel: X轴标签
        ylabel: Y轴标签
        figsize: 图形大小，格式为(宽, 高)
        output_format: 输出格式，可选值：png, svg, pdf
        dpi: 图像DPI（每英寸点数）
        save_path: 保存图像的路径，如果不提供则返回Base64编码的图像数据
        color_map: 颜色映射名称，用于热图和某些多系列图表
        grid: 是否显示网格线
        legend: 是否显示图例
    
    Returns:
        Dict[str, Any]: 包含图像数据或文件路径的字典
    """
    try:
        # 创建图形
        fig = Figure(figsize=figsize)
        ax = fig.add_subplot(111)
        
        # 设置标题和轴标签
        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)
        
        # 设置网格
        ax.grid(grid)
        
        # 根据图表类型绘制
        if chart_type == 'bar':
            # 预期数据格式: {"categories": [...], "values": [...], "series": {...}}
            categories = data.get('categories', [])
            values = data.get('values', [])
            series = data.get('series', {})
            
            if series:
                # 多系列条形图
                x = range(len(categories))
                width = 0.8 / len(series)
                offset = -0.4 + width/2
                
                for i, (series_name, series_values) in enumerate(series.items()):
                    ax.bar([pos + offset + i*width for pos in x], series_values, width=width, label=series_name)
                
                ax.set_xticks(x)
                ax.set_xticklabels(categories)
            else:
                # 单系列条形图
                ax.bar(categories, values)
        
        elif chart_type == 'line':
            # 预期数据格式: {"x": [...], "y": [...], "series": {...}}
            x = data.get('x', [])
            y = data.get('y', [])
            series = data.get('series', {})
            
            if series:
                # 多系列线图
                for series_name, series_values in series.items():
                    ax.plot(x, series_values, label=series_name)
            else:
                # 单系列线图
                ax.plot(x, y)
        
        elif chart_type == 'scatter':
            # 预期数据格式: {"x": [...], "y": [...], "sizes": [...], "colors": [...]}
            x = data.get('x', [])
            y = data.get('y', [])
            sizes = data.get('sizes', None)
            colors = data.get('colors', None)
            
            ax.scatter(x, y, s=sizes, c=colors, cmap=color_map)
            
            # 如果提供了颜色数据，添加颜色条
            if colors is not None:
                fig.colorbar(ax.collections[0], ax=ax)
        
        elif chart_type == 'pie':
            # 预期数据格式: {"labels": [...], "values": [...]}
            labels = data.get('labels', [])
            values = data.get('values', [])
            
            ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')  # 确保饼图是圆的
        
        elif chart_type == 'heatmap':
            # 预期数据格式: {"matrix": [[...]], "x_labels": [...], "y_labels": [...]}
            matrix = data.get('matrix', [])
            x_labels = data.get('x_labels', [])
            y_labels = data.get('y_labels', [])
            
            im = ax.imshow(matrix, cmap=color_map)
            
            # 设置刻度标签
            if x_labels:
                ax.set_xticks(range(len(x_labels)))
                ax.set_xticklabels(x_labels)
            if y_labels:
                ax.set_yticks(range(len(y_labels)))
                ax.set_yticklabels(y_labels)
            
            # 添加颜色条
            fig.colorbar(im, ax=ax)
        
        elif chart_type == 'histogram':
            # 预期数据格式: {"values": [...], "bins": int, "density": bool}
            values = data.get('values', [])
            bins = data.get('bins', 10)
            density = data.get('density', False)
            
            ax.hist(values, bins=bins, density=density)
        
        else:
            return {
                "status": "error",
                "error_type": "ValueError",
                "error_message": f"不支持的图表类型: {chart_type}"
            }
        
        # 添加图例
        if legend and (chart_type == 'line' or (chart_type == 'bar' and data.get('series'))):
            ax.legend()
        
        # 保存或返回图像
        if save_path:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            fig.savefig(save_path, format=output_format, dpi=dpi, bbox_inches='tight')
            return {
                "status": "success",
                "file_path": save_path,
                "message": f"图表已保存到 {save_path}"
            }
        else:
            # 返回Base64编码的图像
            buf = io.BytesIO()
            fig.savefig(buf, format=output_format, dpi=dpi, bbox_inches='tight')
            buf.seek(0)
            img_data = base64.b64encode(buf.read()).decode('utf-8')
            return {
                "status": "success",
                "image_data": img_data,
                "image_format": output_format,
                "image_size": len(img_data)
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }