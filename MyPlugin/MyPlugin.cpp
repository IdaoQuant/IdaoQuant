// choice1.cpp : Defines the entry point for the DLL application.
// ���ʵ��

#include "stdafx.h"
#include "plugin.h"
#include <stdio.h>
#include <stdlib.h>

#define PLUGIN_EXPORTS

BOOL APIENTRY DllMain(HANDLE hModule,
DWORD  ul_reason_for_call,
        LPVOID lpReserved
)
{
switch (ul_reason_for_call)
{
case DLL_PROCESS_ATTACH:
case DLL_THREAD_ATTACH:
case DLL_THREAD_DETACH:
case DLL_PROCESS_DETACH:
break;
}
return TRUE;
}

PDATAIOFUNC	 g_pFuncCallBack;

//��ȡ�ص�����
void RegisterDataInterface(PDATAIOFUNC pfn)
{
    g_pFuncCallBack = pfn;
}



//ע������Ϣ
void GetCopyRightInfo(LPPLUGIN info)
{
    //��д������Ϣ
    strcpy(info->Name, "��һ��");
    strcpy(info->Dy, "Wenling");
    strcpy(info->Author, "IDAO");
    strcpy(info->Period, "���ս���");
    strcpy(info->Descript, "0.��K����ͣ��standonDailyLimit��1.��������/ʮ���ǣ�yesterdaySafe�� 2.��ʷ��Ҫ����λ");
    strcpy(info->OtherInfo, "�Զ���");
    //��д������Ϣ �����ò�����ʾ��Ҫѡ�����һ�ɵ�ǿ��

    info->ParamNum = 1;
    strcpy(info->ParamInfo[0].acParaName, "��K���췶Χ��3��-200�죩");
    info->ParamInfo[0].nMax = 3;
    info->ParamInfo[0].nMax = 200;
    info->ParamInfo[0].nDefault = 10;
}

////////////////////////////////////////////////////////////////////////////////
//�Զ���ʵ��ϸ�ں���(�ɸ���ѡ����Ҫ���)

const	BYTE	g_nAvoidMask[] = { 0xF8,0xF8,0xF8,0xF8 };	// ��Ч���ݱ�־(ϵͳ����)


BOOL standOnDailyLimit(float* price, long max) {
    float lowest = 100;
    for (int i = 0; i < max; i++) {
        if (i > 0) {
            float increase = (price[i] - price[i - 1]) / price[i - 1];
            if (increase > 0.095) {  //�ж���ͣ
                lowest = price[i - 1] < lowest ? price[i - 1] : lowest;
            }
        }
    }
    if (lowest < price[max - 1]) return TRUE;
    else return FALSE;
}

//60�������ڰ�ȫ����������ʮ����
BOOL yesterdaySafe(HISDAT pHisDat) {
    // ��������3������δ��߻��䣬����
    if (pHisDat.Close > pHisDat.Open * 1.03 && !pHisDat.High < pHisDat.Open * 1.07) {
        return FALSE;
    }
    return TRUE;
}

// append new line at the end, or increase the num of corresponding line
void appendLine(Neckline *neckline,float assumeP) {
    for (int i = 0; i < neckline->index; i++) {
        if (neckline->neck_price[i] - assumeP < 0.000001 && neckline->price[i] - assumeP > -0.000001) {
            neckline->neck_price_amount[i]++;
            return;
        }
    }
    neckline->index++;
    neckline->neck_price[neckline->index]=assumeP;

}

Neckline calcNeckline(float* price, long max) {
    // ��¼ÿһ���յ�(����ʹ�õݹ飬���ֳ��������������
    // �����������γɾ���
    // Ŀǰ��5�����������������ϵĵ���������Ϊ��Ч����
    Neckline possiblePoint, neckline, returnNeckline;
    float rised = 0;
    float maxP = price[0];
    float minP = price[0];

    // ����յ�������Сֵ
    for (int i = 1; i < max; i++)
    {
        if (rised * (price[i] - price[i - 1]) < 0) {
            possiblePoint.price[possiblePoint.index] = price[i - 1];
            possiblePoint.index++;
        }
        rised = price[i] - price[i - 1];
        maxP = maxP > price[i] ? maxP : price[i];
        minP = minP < price[i] ? minP : price[i];
    }

    // neckline to iterate through possible turning point
    // magic number to be fixed. 1. areas:20  2. amplitude:0.01
    for (int i = 0; i < 20; i++) {
        float assumeP = maxP - (maxP - minP) * i / 20;
        float upperBound = assumeP * 1.01;
        float lowerBound = assumeP * 0.99;
        for (int j = 0; j <= possiblePoint.index; j++) {
            appendLine(&neckline, assumeP);
        }
    }

    for (int i = 0; i < neckline.index;i++) {
        if(neckline.neck_price_amount[i] > 5) {  // 5: min num of turning point falls on neckline
            appendLine(&returnNeckline, neckline.neck_price[i]);
        }
    }
    return returnNeckline;
}


BOOL yesterdayOnNeckline(float *price,long max) {
    Neckline neckline = calcNeckline(price, max);
    for (int i = 0;i < neckline.index; i++) {
        if (price[max-1] < price[i]*1.01 && price[max-1] > price[i]* 0.99)
            return TRUE;
    }
    return FALSE;
}


BOOL InputInfoThenCalc1(char* Code, short nSetCode, int Value[4], short DataType, short nDataNum, BYTE nTQ, unsigned long unused) //��������ݼ���
{
    BOOL nRet = FALSE;
    NTime tmpTime = { 0 };
    BOOL condition[2];// index˵����Ӧdescription
    LPHISDAT pHisDat = new HISDAT[nDataNum];  //���ݻ����� ÿ��hisdatΪһ��k�ߵ�������Ϣ
    long readnum = g_pFuncCallBack(Code, nSetCode, DataType, pHisDat, nDataNum, tmpTime, tmpTime, nTQ, 0);  //���ûص������������ݣ����صõ������ݸ���
    if (readnum > max(Value[0], Value[1])) //ֻ�����ݸ�������Value[0]��Value[1]�е����ֵ��������
    {
        float* price = new float[readnum];
        for (int i = 0; i < readnum; i++) //�����̼۵�������
        {
            price[i] = pHisDat[i].Close;
        }

        condition[0] = standOnDailyLimit(price, readnum);
        condition[1] = yesterdaySafe(pHisDat[readnum - 1]);


    }

    if (condition[0] || condition[1]) nRet = TRUE;
    delete[]pHisDat; pHisDat = NULL;
    return nRet;
}
