/**************************************************/
/*		PLUGIN��̬���ӿ⵼��ͷ�ļ�				  */
/**************************************************/

#ifndef PLUGIN_H_
#define PLUGIN_H_

#ifdef PLUGIN_EXPORTS
#define PLUGIN_API extern "C"  __declspec(dllexport)
#else
#define PLUGIN_API extern "C" __declspec(dllimport)
#endif

#include "OutStruct.h"

#pragma pack(push,1)

//vector
typedef struct vector
{
	float price[200] = {0};           // save all price
	float neck_price[200] = {0};      // possible neck price
	int neck_price_amount[200] = {0}; // corresponding neck price amount
	int index = 0;
}Neckline;


typedef struct tag_PluginPara	//������Ϣ�Ľṹ����
{
	char  acParaName[14];		//��������������
	int   nMin;					//������Сȡֵ��Χ
	int   nMax;					//�������ȡֵ��Χ
	int   nDefault;				//ϵͳ�Ƽ���ȱʡֵ
	int   nValue;				//�û������ֵ
}PLUGINPARAM;

typedef struct tag_PlugInfo
{
	char  Name[50];				//������汾
	char  Dy[30];				//����
	char  Author[30];			//�����
	char  Descript[100];		//ѡ������
	char  Period[30];			//��Ӧ����
	char  OtherInfo[300];
	short ParamNum;				//0<=��������<=4
	PLUGINPARAM ParamInfo[4];	//������Ϣ������
}PLUGIN,*LPPLUGIN;

//�ص�����,ȡ���ݽӿ�
typedef long(CALLBACK * PDATAIOFUNC)(char * Code,short nSetCode,short DataType,void * pData,short nDataNum,NTime,NTime,BYTE nTQ,unsigned long);
//ע��ص�����
PLUGIN_API void  RegisterDataInterface(PDATAIOFUNC pfn);
//�õ���Ȩ��Ϣ
PLUGIN_API void	 GetCopyRightInfo(LPPLUGIN info);
//��������ݼ���(nDataNumΪASK_ALL��ʾ��������)
PLUGIN_API BOOL	 InputInfoThenCalc1(char * Code,short nSetCode,int Value[4],short DataType,short nDataNum,BYTE nTQ,unsigned long unused);
//ѡȡ���μ���
PLUGIN_API BOOL	 InputInfoThenCalc2(char * Code,short nSetCode,int Value[4],short DataType,NTime time1,NTime time2,BYTE nTQ,unsigned long unused); 


#pragma pack(pop)
#endif
